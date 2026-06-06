"""
cache.py — Optimised data fetching layer for the MEC Student Portal.

Key improvements over basic version:
  1. Persistent requests.Session with connection pooling — reuses TCP connections
  2. Retry logic with backoff — handles Google Apps Script cold starts gracefully
  3. Last-known-good fallback — never returns empty if we have previous good data
  4. Optimised TTLs — tuned per data type based on how often each changes
  5. Files cached for 1 hour — uploaded files never change once stored
  6. All fetchers return safe empty defaults on total failure
"""

import time
import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────
WEBHOOK_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbyNSSTRMkXx3aQeK-9ow5xKACWYPnXkV8L-JGRNyLVkyXHx3gzViCJFGVJ3BhT1dg_h/exec"
)

EMPTY_COLUMNS = [
    "Timestamp", "Student Name", "Reg Number",
    "Course Code", "Contact", "Assigned Group"
]

# TTL values tuned per data type
TTL_ROSTER        = 120   # 2 min  — changes only on register/delete/group update
TTL_ANNOUNCEMENTS = 45    # 45 sec — reps post occasionally
TTL_MATERIALS     = 120   # 2 min  — files rarely added
TTL_FEEDBACK      = 45    # 45 sec — students send messages occasionally
TTL_RECEIPTS      = 60    # 1 min  — read receipts
TTL_FILE          = 3600  # 1 hour — uploaded files never change once stored
TTL_REP_REPLIES   = 45    # 45 sec — rep replies polled frequently by students

# ─────────────────────────────────────────────────────────────
# PERSISTENT HTTP SESSION WITH CONNECTION POOLING + RETRY
# ─────────────────────────────────────────────────────────────
# One session shared across ALL requests in the process.
# Reuses TCP connections — eliminates handshake overhead on repeat calls.
# Retries up to 3 times on connection errors and 502/503/504 (GAS cold starts).

def _build_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=3,                            # max 3 retries
        backoff_factor=0.4,                 # wait 0.4s, 0.8s, 1.6s between retries
        status_forcelist=[429, 500, 502, 503, 504],  # retry on these HTTP codes
        allowed_methods=["GET", "POST"],
        raise_on_status=False
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=4,   # number of connection pools
        pool_maxsize=8        # max connections per pool
    )
    session.mount("https://", adapter)
    session.mount("http://",  adapter)
    return session

# Module-level session — created once, reused forever
_SESSION = _build_session()


# ─────────────────────────────────────────────────────────────
# LAST-KNOWN-GOOD STORE
# ─────────────────────────────────────────────────────────────
# If a fetch fails completely, we return the last successful
# result instead of empty data — keeps the UI usable during
# temporary Google Apps Script outages.

_last_good: dict = {
    "roster":        None,
    "announcements": None,
    "materials":     None,
    "feedback":      None,
    "receipts":      None,
    "rep_replies":   None,
}


def _get(url: str, timeout: int = 15):
    """Shared GET helper using the pooled session."""
    return _SESSION.get(url, timeout=timeout)


# ─────────────────────────────────────────────────────────────
# CACHED FETCHERS
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=TTL_ROSTER, show_spinner=False)
def cached_fetch_roster() -> pd.DataFrame:
    try:
        r = _get(WEBHOOK_URL)
        if r.status_code == 200:
            data = r.json()
            if data:
                df = pd.DataFrame(data)
                _last_good["roster"] = df
                return df
        # Fall back to last known good
        if _last_good["roster"] is not None:
            return _last_good["roster"]
        return pd.DataFrame(columns=EMPTY_COLUMNS)
    except Exception as e:
        print(f"[cache] Roster fetch error: {e}")
        if _last_good["roster"] is not None:
            return _last_good["roster"]
        return pd.DataFrame(columns=EMPTY_COLUMNS)


@st.cache_data(ttl=TTL_ANNOUNCEMENTS, show_spinner=False)
def cached_fetch_announcements() -> list:
    try:
        r = _get(f"{WEBHOOK_URL}?action=getAnnouncements")
        if r.status_code == 200:
            raw    = r.json()
            result = []
            if isinstance(raw, list):
                for row in raw:
                    if isinstance(row, list) and len(row) >= 2:
                        result.append({
                            "timestamp": str(row[0]).strip(),
                            "text":      str(row[1]).strip(),
                            "priority":  str(row[2]).strip() if len(row) >= 3 else "Normal"
                        })
                    elif isinstance(row, dict):
                        result.append({
                            "timestamp": str(row.get("timestamp", "")).strip(),
                            "text":      str(row.get("text", "")).strip(),
                            "priority":  str(row.get("priority", "Normal")).strip()
                        })
                    elif isinstance(row, str):
                        result.append({"timestamp": "", "text": row.strip(), "priority": "Normal"})
            out = result[::-1]
            _last_good["announcements"] = out
            return out
        if _last_good["announcements"] is not None:
            return _last_good["announcements"]
        return []
    except Exception as e:
        print(f"[cache] Announcements fetch error: {e}")
        return _last_good["announcements"] or []


@st.cache_data(ttl=TTL_MATERIALS, show_spinner=False)
def cached_fetch_materials() -> list:
    try:
        r = _get(f"{WEBHOOK_URL}?action=getMaterials")
        if r.status_code == 200:
            raw       = r.json()
            materials = []
            if isinstance(raw, list):
                for row in raw:
                    if isinstance(row, dict):
                        materials.append({
                            "name": row.get("name", "Unnamed"),
                            "url":  row.get("url", "#")
                        })
                    elif isinstance(row, list) and len(row) >= 2:
                        materials.append({
                            "name": str(row[0]).strip(),
                            "url":  str(row[1]).strip()
                        })
            out = materials[::-1]
            _last_good["materials"] = out
            return out
        if _last_good["materials"] is not None:
            return _last_good["materials"]
        return []
    except Exception as e:
        print(f"[cache] Materials fetch error: {e}")
        return _last_good["materials"] or []


@st.cache_data(ttl=TTL_FEEDBACK, show_spinner=False)
def cached_fetch_feedback() -> list:
    try:
        r = _get(f"{WEBHOOK_URL}?action=getFeedback")
        if r.status_code == 200:
            out = r.json()[::-1]
            _last_good["feedback"] = out
            return out
        if _last_good["feedback"] is not None:
            return _last_good["feedback"]
        return []
    except Exception as e:
        print(f"[cache] Feedback fetch error: {e}")
        return _last_good["feedback"] or []


@st.cache_data(ttl=TTL_RECEIPTS, show_spinner=False)
def cached_fetch_read_receipts() -> list:
    try:
        r = _get(f"{WEBHOOK_URL}?action=getReadReceipts")
        if r.status_code == 200:
            out = r.json()
            _last_good["receipts"] = out
            return out
        if _last_good["receipts"] is not None:
            return _last_good["receipts"]
        return []
    except Exception as e:
        print(f"[cache] Read receipts fetch error: {e}")
        return _last_good["receipts"] or []


@st.cache_data(ttl=TTL_FILE, show_spinner=False)
def cached_fetch_file(url: str) -> bytes:
    """
    Files are cached for 1 hour — once uploaded they never change.
    Uses a longer timeout since Drive files can be large.
    """
    try:
        r = _SESSION.get(url, timeout=30)
        return r.content
    except Exception as e:
        print(f"[cache] File fetch error ({url[:40]}...): {e}")
        return b""


@st.cache_data(ttl=TTL_REP_REPLIES, show_spinner=False)
def cached_fetch_rep_replies(reg_number: str = None) -> list:
    """
    Fetch rep replies from the RepReplies sheet.
    If reg_number is provided, only replies addressed to that student are returned.
    If None, all replies are returned (used by rep for overview).
    """
    try:
        url = f"{WEBHOOK_URL}?action=getRepReplies"
        if reg_number:
            url += f"&reg_number={reg_number}"
        r = _get(url)
        if r.status_code == 200:
            out = r.json()
            if isinstance(out, list):
                out = out[::-1]  # newest first
                _last_good["rep_replies"] = out
                return out
        if _last_good["rep_replies"] is not None:
            return _last_good["rep_replies"]
        return []
    except Exception as e:
        print(f"[cache] Rep replies fetch error: {e}")
        return _last_good["rep_replies"] or []
