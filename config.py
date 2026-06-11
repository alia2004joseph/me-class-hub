"""
config.py — Central configuration for the Smart University App.

TO ADD A NEW DEPARTMENT:
  1. Add one entry to DEPARTMENTS below.
  2. That's it. Everything else (UI colours, dropdowns, filters) picks it up automatically.

TO ADD A NEW YEAR LEVEL:
  1. Add one string to YEARS below.
"""

# ─────────────────────────────────────────────────────────────
# DEPARTMENTS
# Each key is the short code used throughout the app and in Sheets.
# ─────────────────────────────────────────────────────────────
DEPARTMENTS: dict = {
    "MEC": {
        "name":    "Mechanical Engineering",
        "color":   "#1a56db",   # blue
        "light":   "#dbeafe",
        "courses": ["BMEC", "BBPE", "BWIE", "BAGE"],
    },
    "ELE": {
        "name":    "Electrical Engineering",
        "color":   "#16a34a",   # green
        "light":   "#dcfce7",
        "courses": ["BELE", "BTEL", "BPOW"],
    },
    "CIV": {
        "name":    "Civil Engineering",
        "color":   "#ea580c",   # orange
        "light":   "#ffedd5",
        "courses": ["BCIV", "BSTR", "BENV"],
    },
    "OTH": {
        "name":    "Others",
        "color":   "#7c3aed",   # purple
        "light":   "#ede9fe",
        "courses": ["OTHER"],
    },
}

# ─────────────────────────────────────────────────────────────
# YEAR LEVELS
# ─────────────────────────────────────────────────────────────
YEARS: list = ["Year 1", "Year 2", "Year 3", "Year 4"]

# ─────────────────────────────────────────────────────────────
# HELPERS  (used by UI and database layers)
# ─────────────────────────────────────────────────────────────
DEPT_NAMES:   dict = {k: v["name"]    for k, v in DEPARTMENTS.items()}
DEPT_CODES:   list = list(DEPARTMENTS.keys())
DEPT_COLORS:  dict = {k: v["color"]   for k, v in DEPARTMENTS.items()}
DEPT_LIGHTS:  dict = {k: v["light"]   for k, v in DEPARTMENTS.items()}
DEPT_COURSES: dict = {k: v["courses"] for k, v in DEPARTMENTS.items()}

# Flat list of all course codes across all departments
ALL_COURSES: list = [c for v in DEPARTMENTS.values() for c in v["courses"]]

def get_dept_for_course(course_code: str) -> str:
    """Return the department code for a given course code."""
    for dept, v in DEPARTMENTS.items():
        if course_code.upper() in v["courses"]:
            return dept
    return "OTH"

def dept_color(dept_code: str) -> str:
    return DEPARTMENTS.get(dept_code, DEPARTMENTS["OTH"])["color"]

def dept_light(dept_code: str) -> str:
    return DEPARTMENTS.get(dept_code, DEPARTMENTS["OTH"])["light"]

def dept_name(dept_code: str) -> str:
    return DEPARTMENTS.get(dept_code, DEPARTMENTS["OTH"])["name"]

def dept_courses(dept_code: str) -> list:
    return DEPARTMENTS.get(dept_code, DEPARTMENTS["OTH"])["courses"]