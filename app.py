"""
app.py — Smart University App entry point.
Roles: Student | Class Rep | Super Admin
"""
import streamlit as st

st.set_page_config(
    page_title="Smart University App",
    page_icon="🎓",
    layout="centered"
)

from database   import SheetDatabaseManager
from ai_engine  import AISortingEngine, AIStudyAssistant, AIRepAssistant, AIAdminAssistant
from student    import render_student_interface
from class_rep  import render_class_rep_interface
from Superadmin import render_superadmin_interface
from config     import get_departments

# ── Shared managers ───────────────────────────────────────────
db       = SheetDatabaseManager()
ai       = AISortingEngine()
ai_study = AIStudyAssistant()
ai_rep   = AIRepAssistant()
ai_admin = AIAdminAssistant()

# ── Global CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Plus Jakarta Sans',sans-serif;}
#MainMenu,footer{visibility:hidden;}
[data-testid="stSidebar"]{background:#0f172a;}
[data-testid="stSidebar"] *{color:white !important;}
[data-testid="stSidebar"] .stRadio label{color:white !important;font-weight:600;}
</style>
""", unsafe_allow_html=True)

# ── Session defaults ──────────────────────────────────────────
if "role" not in st.session_state:
    st.session_state.role = "Student"

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:20px 0 10px 0;">
        <div style="font-size:2.5rem;">🎓</div>
        <div style="font-size:1.1rem;font-weight:800;color:white;margin-top:6px;">Smart University</div>
        <div style="font-size:0.75rem;color:rgba(255,255,255,0.5);margin-top:2px;">Class Management Portal</div>
    </div>
    <hr style="border-color:rgba(255,255,255,0.1);margin:10px 0 20px 0;">
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;color:rgba(255,255,255,0.4);margin-bottom:8px;">Select Your Role</div>', unsafe_allow_html=True)

    st.session_state.role = st.radio(
        "Role", ["Student", "Class Rep", "Super Admin"],
        label_visibility="collapsed"
    )

    role_info = {
        "Student":     ("🎓", "View notices, download materials, message your rep and use the AI study assistant."),
        "Class Rep":   ("👑", "Manage your class roster, post announcements, upload materials and reply to students."),
        "Super Admin": ("🛡️", "Oversee all departments, manage rep accounts and broadcast university-wide notices."),
    }
    icon, desc = role_info[st.session_state.role]
    st.markdown(f"""
    <hr style="border-color:rgba(255,255,255,0.1);margin:16px 0;">
    <div style="background:rgba(255,255,255,0.06);border-radius:10px;padding:14px;">
        <div style="font-size:1.4rem;margin-bottom:6px;">{icon}</div>
        <div style="font-size:0.8rem;color:rgba(255,255,255,0.6);line-height:1.5;">{desc}</div>
    </div>
    <hr style="border-color:rgba(255,255,255,0.1);margin:16px 0 12px 0;">
    <div style="font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;color:rgba(255,255,255,0.4);margin-bottom:10px;">Departments</div>
    """, unsafe_allow_html=True)

    for code, info in get_departments().items():
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <div style="width:10px;height:10px;border-radius:50%;background:{info['color']};flex-shrink:0;"></div>
            <div style="font-size:0.78rem;color:rgba(255,255,255,0.7);">{info['name']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <hr style="border-color:rgba(255,255,255,0.1);margin:16px 0 10px 0;">
    <div style="font-size:0.68rem;color:rgba(255,255,255,0.25);text-align:center;">
        Smart University App v2.0<br>Designed by ALIA JOSEPH
    </div>
    """, unsafe_allow_html=True)

# ── Page header ───────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#0f172a 0%,#1a56db 100%);
    border-radius:16px;padding:24px 28px;margin-bottom:20px;color:white;">
    <div style="font-size:0.72rem;letter-spacing:2px;text-transform:uppercase;opacity:0.6;margin-bottom:6px;">
        University Class Management
    </div>
    <div style="font-size:1.6rem;font-weight:800;margin-bottom:4px;">🎓 Smart University App</div>
    <div style="font-size:0.85rem;opacity:0.65;">
        Student Portal · Class Rep Dashboard · Admin Console
    </div>
</div>
""", unsafe_allow_html=True)

# ── Fetch full roster for student login lookup ────────────────
df_profiles = db.fetch_roster(dept="ALL", year="ALL")

# ── Route by role ─────────────────────────────────────────────
if st.session_state.role == "Student":
    render_student_interface(db, ai_study, df_profiles)

elif st.session_state.role == "Class Rep":
    render_class_rep_interface(db, ai, ai_rep)

elif st.session_state.role == "Super Admin":
    render_superadmin_interface(db, ai_admin)