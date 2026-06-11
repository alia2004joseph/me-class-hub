"""
cache.py — Optimised, dept+year-aware data fetching layer.
Read receipts removed. Reps cache added.
"""

import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─────────────────────────────────────────────────────────────
# CONFIGURATION  — update WEBHOOK_URL after redeploying GAS
# ─────────────────────────────────────────────────────────────
WEBHOOK_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbyNSSTRMkXx3aQeK-9ow5xKACWYPnXkV8L-JGRNyLVkyXHx3gzViCJFGVJ3BhT1dg_h/exec"
)

EMPTY_COLUMNS = [
    "Timestamp", "Student Name", "Reg Number",
    "Course Code", "Contact", "Assigned Group",
    "Department", "Year"
]

TTL_ROSTER        = 120   # 2 min
TTL_ANNOUNCEMENTS = 45    # 45 sec
TTL_MATERIALS     = 120   # 2 min
TTL_FEEDBACK      = 45    # 45 sec
TTL_FILE          = 3600  # 1 hour
TTL_REP_REPLIES   = 45    # 45 sec
TTL_REPS          = 60    # 1 min — rep accounts change infrequently

# ─────────────────────────────────────────────────────────────
# PERSISTENT HTTP SESSION
# ─────────────────────────────────────────────────────────────
def _build_session() -> requests.Session:
    session = requests.Session()
    retry   = Retry(
        total=3, backoff_factor=0.4,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"], raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=8)
    session.mount("https://", adapter)
    session.mount("http://",  adapter)
    return session

_SESSION = _build_session()

# ─────────────────────────────────────────────────────────────
# LAST-KNOWN-GOOD STORE
# ─────────────────────────────────────────────────────────────
_last_good: dict = {
    "roster":        {},
    "announcements": {},
    "materials":     {},
    "feedback":      {},
    "rep_replies":   {},
    "reps":          None,
}

def _get(url: str, timeout: int = 15):
    return _SESSION.get(url, timeout=timeout)


# ─────────────────────────────────────────────────────────────
# CACHED FETCHERS
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=TTL_ROSTER, show_spinner=False)
def cached_fetch_roster(dept: str = "ALL", year: str = "ALL") -> pd.DataFrame:
    try:
        url = WEBHOOK_URL
        params = []
        if dept != "ALL": params.append(f"dept={dept}")
        if year != "ALL": params.append(f"year={year}")
        if params: url += "?" + "&".join(params)

        r = _get(url)
        if r.status_code == 200:
            data = r.json()
            if data:
                df = pd.DataFrame(data)
                _last_good["roster"][(dept, year)] = df
                return df
        cached = _last_good["roster"].get((dept, year))
        return cached if cached is not None else pd.DataFrame(columns=EMPTY_COLUMNS)
    except Exception as e:
        print(f"[cache] Roster fetch error: {e}")
        cached = _last_good["roster"].get((dept, year))
        return cached if cached is not None else pd.DataFrame(columns=EMPTY_COLUMNS)


@st.cache_data(ttl=TTL_ANNOUNCEMENTS, show_spinner=False)
def cached_fetch_announcements(dept: str = "ALL", year: str = "ALL") -> list:
    try:
        url = f"{WEBHOOK_URL}?action=getAnnouncements"
        if dept != "ALL": url += f"&dept={dept}"
        if year != "ALL": url += f"&year={year}"

        r = _get(url)
        if r.status_code == 200:
            raw    = r.json()
            result = []
            if isinstance(raw, list):
                for row in raw:
                    if isinstance(row, dict):
                        result.append({
                            "timestamp": str(row.get("timestamp", "")).strip(),
                            "text":      str(row.get("text",      "")).strip(),
                            "priority":  str(row.get("priority",  "Normal")).strip(),
                            "dept":      str(row.get("dept",      dept)).strip(),
                            "year":      str(row.get("year",      year)).strip(),
                        })
            _last_good["announcements"][(dept, year)] = result
            return result
        cached = _last_good["announcements"].get((dept, year))
        return cached if cached is not None else []
    except Exception as e:
        print(f"[cache] Announcements fetch error: {e}")
        return _last_good["announcements"].get((dept, year)) or []


@st.cache_data(ttl=TTL_MATERIALS, show_spinner=False)
def cached_fetch_materials(dept: str = "ALL", year: str = "ALL") -> list:
    try:
        url = f"{WEBHOOK_URL}?action=getMaterials"
        if dept != "ALL": url += f"&dept={dept}"
        if year != "ALL": url += f"&year={year}"

        r = _get(url)
        if r.status_code == 200:
            raw  = r.json()
            mats = []
            if isinstance(raw, list):
                for row in raw:
                    if isinstance(row, dict):
                        mats.append({
                            "name": str(row.get("name", "Unnamed")).strip(),
                            "url":  str(row.get("url",  "#")).strip(),
                            "dept": str(row.get("dept", dept)).strip(),
                            "year": str(row.get("year", year)).strip(),
                        })
            _last_good["materials"][(dept, year)] = mats
            return mats
        cached = _last_good["materials"].get((dept, year))
        return cached if cached is not None else []
    except Exception as e:
        print(f"[cache] Materials fetch error: {e}")
        return _last_good["materials"].get((dept, year)) or []


@st.cache_data(ttl=TTL_FEEDBACK, show_spinner=False)
def cached_fetch_feedback(dept: str = "ALL", year: str = "ALL") -> list:
    try:
        url = f"{WEBHOOK_URL}?action=getFeedback"
        if dept != "ALL": url += f"&dept={dept}"
        if year != "ALL": url += f"&year={year}"

        r = _get(url)
        if r.status_code == 200:
            out = r.json()
            if isinstance(out, list):
                _last_good["feedback"][(dept, year)] = out
                return out
        cached = _last_good["feedback"].get((dept, year))
        return cached if cached is not None else []
    except Exception as e:
        print(f"[cache] Feedback fetch error: {e}")
        return _last_good["feedback"].get((dept, year)) or []


@st.cache_data(ttl=TTL_FILE, show_spinner=False)
def cached_fetch_file(url: str) -> bytes:
    try:
        r = _SESSION.get(url, timeout=30)
        return r.content
    except Exception as e:
        print(f"[cache] File fetch error: {e}")
        return b""


@st.cache_data(ttl=TTL_REP_REPLIES, show_spinner=False)
def cached_fetch_rep_replies(
    reg_number: str = None,
    dept: str = "ALL",
    year: str = "ALL"
) -> list:
    try:
        url = f"{WEBHOOK_URL}?action=getRepReplies"
        if reg_number:    url += f"&reg_number={reg_number}"
        if dept != "ALL": url += f"&dept={dept}"
        if year != "ALL": url += f"&year={year}"

        r = _get(url)
        if r.status_code == 200:
            out = r.json()
            if isinstance(out, list):
                _last_good["rep_replies"][(dept, year)] = out
                return out
        cached = _last_good["rep_replies"].get((dept, year))
        return cached if cached is not None else []
    except Exception as e:
        print(f"[cache] Rep replies fetch error: {e}")
        return _last_good["rep_replies"].get((dept, year)) or []


@st.cache_data(ttl=TTL_REPS, show_spinner=False)
def cached_fetch_reps() -> list:
    """Fetch all rep accounts from the Reps Sheet (super admin use)."""
    try:
        r = _get(f"{WEBHOOK_URL}?action=getReps")
        if r.status_code == 200:
            out = r.json()
            if isinstance(out, list):
                _last_good["reps"] = out
                return out
        return _last_good["reps"] or []
    except Exception as e:
        print(f"[cache] Reps fetch error: {e}")
        return _last_good["reps"] or []