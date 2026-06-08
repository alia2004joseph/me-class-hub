import streamlit as st

# ── Page config MUST be first Streamlit call ─────────────────
st.set_page_config(
    page_title="ME Class Hub",
    page_icon="⚙️",
    layout="centered"
)

# ── Imports ──────────────────────────────────────────────────
from database import SheetDatabaseManager
from ai_engine import AISortingEngine
from ai_engine import AIStudyAssistant
from ai_engine import AIRepAssistant
from student import render_student_interface
from class_rep import render_class_rep_interface

st.write("✅ The app is designed by ALIA JOSEPH")

# ── Instantiate managers ─────────────────────────────────────
db       = SheetDatabaseManager()
ai       = AISortingEngine()       # used by class rep for group allocation
ai_study = AIStudyAssistant()      # used by students for AI study assistant
ai_rep   = AIRepAssistant()        # used by class rep for AI admin features

# ── Session state ─────────────────────────────────────────────
if "role" not in st.session_state:
    st.session_state.role = "Student"

if "show_success_message" in st.session_state:
    st.success(f"🎉 Welcome aboard, {st.session_state['show_success_message']}! Profile created.")
    del st.session_state["show_success_message"]

# ── Sidebar ───────────────────────────────────────────────────
st.sidebar.title("🔐 Access Control")
st.session_state.role = st.sidebar.radio(
    "Identify your role:", ["Student", "Class Rep"]
)

st.title("⚙️ MECHANICAL ENGINEERING APP")

# ── Navigation Tabs ───────────────────────────────────────────
tab1, tab2 = st.tabs(["📋 Student Portal", "👑 Class Rep Dashboard"])

# Fetch roster once — shared across both interfaces
df_profiles = db.fetch_roster()

with tab1:
    render_student_interface(db, ai_study, df_profiles)

with tab2:
    render_class_rep_interface(db, ai, ai_rep, df_profiles)