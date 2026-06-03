import streamlit as st
# Import our modular backend + interfaces
from database import SheetDatabaseManager
from ai_engine import AISortingEngine
from student import render_student_interface
from class_rep import render_class_rep_interface



# Quick test to confirm Streamlit runs
st.write("✅ The app is designed by ALIA JOSEPH")


# ---------------------------
# App Configuration
# ---------------------------
st.set_page_config(page_title="ME Class Hub", page_icon="⚙️", layout="centered")

# Instantiate managers
db = SheetDatabaseManager()   # ✅ Consistent backend connector
ai = AISortingEngine()

# Session state handlers
if "role" not in st.session_state:
    st.session_state.role = "Student"
if "show_success_message" in st.session_state:
    st.success(f"🎉 Welcome aboard, {st.session_state['show_success_message']}! Profile created.")
    del st.session_state["show_success_message"]

# ---------------------------
# Sidebar Access Controls
# ---------------------------
st.sidebar.title("🔐 Access Control")
st.session_state.role = st.sidebar.radio("Identify your role:", ["Student", "Class Rep"])

st.title("⚙️ MECHANICAL ENGINEERING APP")

# ---------------------------
# Navigation Tabs
# ---------------------------
tab1, tab2 = st.tabs(["📋 Student Portal", "👑 Class Rep Dashboard"])

# Live database records fetch
df_profiles = db.fetch_roster()

with tab1:
    render_student_interface(db, df_profiles)   # ✅ Student portal

with tab2:
    render_class_rep_interface(db, ai, df_profiles)   # ✅ Class Rep dashboard
