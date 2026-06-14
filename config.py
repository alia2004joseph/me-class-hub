"""
config.py — Dynamic department configuration.
Departments are loaded from Google Sheets at runtime.
Fallback to hardcoded defaults if the sheet is unavailable.
"""
import requests
import streamlit as st

WEBHOOK_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbyNSSTRMkXx3aQeK-9ow5xKACWYPnXkV8L-JGRNyLVkyXHx3gzViCJFGVJ3BhT1dg_h/exec"
)

YEARS = ["Year 1", "Year 2", "Year 3", "Year 4"]

# Preset colour palette for admin to pick from
COLOUR_PALETTE = [
    {"name": "Blue",       "hex": "#1a56db", "light": "#dbeafe"},
    {"name": "Green",      "hex": "#16a34a", "light": "#dcfce7"},
    {"name": "Orange",     "hex": "#ea580c", "light": "#ffedd5"},
    {"name": "Purple",     "hex": "#7c3aed", "light": "#ede9fe"},
    {"name": "Red",        "hex": "#dc2626", "light": "#fee2e2"},
    {"name": "Pink",       "hex": "#db2777", "light": "#fce7f3"},
    {"name": "Teal",       "hex": "#0d9488", "light": "#ccfbf1"},
    {"name": "Indigo",     "hex": "#4338ca", "light": "#e0e7ff"},
    {"name": "Yellow",     "hex": "#b45309", "light": "#fef3c7"},
    {"name": "Cyan",       "hex": "#0284c7", "light": "#e0f2fe"},
    {"name": "Rose",       "hex": "#e11d48", "light": "#ffe4e6"},
    {"name": "Slate",      "hex": "#475569", "light": "#f1f5f9"},
]

# Hardcoded fallback — used if Departments sheet is unavailable
FALLBACK_DEPARTMENTS = {
    "MEC": {"name": "Mechanical Engineering", "color": "#1a56db",
            "light": "#dbeafe", "courses": ["BMEC","BBPE","BWIE","BAGE"]},
    "ELE": {"name": "Electrical Engineering",  "color": "#16a34a",
            "light": "#dcfce7", "courses": ["BELE","BTEL","BPOW"]},
    "CIV": {"name": "Civil Engineering",       "color": "#ea580c",
            "light": "#ffedd5", "courses": ["BCIV","BSTR","BENV"]},
    "OTH": {"name": "Others",                  "color": "#7c3aed",
            "light": "#ede9fe", "courses": ["OTHER"]},
}


@st.cache_data(ttl=120, show_spinner=False)
def load_departments() -> dict:
    """
    Load departments from Google Sheets.
    Falls back to FALLBACK_DEPARTMENTS if unavailable.
    """
    try:
        r = requests.get(f"{WEBHOOK_URL}?action=getDepartments", timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                depts = {}
                for row in data:
                    code    = str(row.get("code", "")).strip().upper()
                    if not code: continue
                    courses_raw = row.get("courses", "")
                    courses = [c.strip().upper() for c in str(courses_raw).split(",") if c.strip()]
                    depts[code] = {
                        "name":    str(row.get("name",  code)).strip(),
                        "color":   str(row.get("color", "#1a56db")).strip(),
                        "light":   str(row.get("light", "#dbeafe")).strip(),
                        "courses": courses if courses else ["OTHER"],
                    }
                if depts:
                    return depts
    except Exception as e:
        print(f"[config] Departments fetch error: {e}")
    return FALLBACK_DEPARTMENTS


def get_departments() -> dict:
    return load_departments()

def get_dept_codes() -> list:
    return list(load_departments().keys())

def dept_color(code: str) -> str:
    return load_departments().get(code, FALLBACK_DEPARTMENTS.get("OTH", {})).get("color", "#1a56db")

def dept_light(code: str) -> str:
    return load_departments().get(code, FALLBACK_DEPARTMENTS.get("OTH", {})).get("light", "#dbeafe")

def dept_name(code: str) -> str:
    return load_departments().get(code, FALLBACK_DEPARTMENTS.get("OTH", {})).get("name", code)

def dept_courses(code: str) -> list:
    return load_departments().get(code, FALLBACK_DEPARTMENTS.get("OTH", {})).get("courses", ["OTHER"])

def get_all_courses() -> list:
    return [c for v in load_departments().values() for c in v.get("courses", [])]