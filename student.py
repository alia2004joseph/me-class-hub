import streamlit as st
from database import SheetDatabaseManager
from cache import cached_fetch_feedback, cached_fetch_rep_replies


# ─────────────────────────────────────────
# CSS Injection
# ─────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    #MainMenu, footer { visibility: hidden; }
    .stApp { background: #F0F4FF; }

    .welcome-banner {
        background: linear-gradient(135deg, #1a56db 0%, #0e3fad 100%);
        border-radius: 18px; padding: 28px 32px; margin-bottom: 24px;
        position: relative; overflow: hidden; color: white;
    }
    .welcome-banner::before {
        content: ""; position: absolute; top: -40px; right: -40px;
        width: 180px; height: 180px; border-radius: 50%;
        background: rgba(255,255,255,0.06);
    }
    .welcome-banner::after {
        content: ""; position: absolute; bottom: -30px; left: 60%;
        width: 120px; height: 120px; border-radius: 50%;
        background: rgba(255,255,255,0.04);
    }
    .welcome-banner .wb-label {
        font-size: 0.72rem; letter-spacing: 2px;
        text-transform: uppercase; opacity: 0.7; margin-bottom: 6px;
    }
    .welcome-banner h2 { font-size: 1.7rem; font-weight: 800; margin: 0 0 6px 0; color: white; }
    .welcome-banner p  { font-size: 0.88rem; opacity: 0.75; margin: 0 0 14px 0; }
    .pill-strip { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
    .pill {
        background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25);
        border-radius: 20px; padding: 4px 14px; font-size: 0.75rem; font-weight: 600; color: white;
    }
    .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
    .stat-card {
        background: white; border-radius: 14px; padding: 18px 14px; text-align: center;
        border: 1px solid #e2e8f7; box-shadow: 0 2px 8px rgba(26,86,219,0.06);
    }
    .stat-card .s-icon { font-size: 1.6rem; margin-bottom: 6px; }
    .stat-card .s-val  { font-size: 1.45rem; font-weight: 800; color: #1a56db; line-height: 1; margin-bottom: 4px; }
    .stat-card .s-label { font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
    .sec-header {
        display: flex; align-items: center; gap: 10px;
        margin: 4px 0 14px 0; padding-bottom: 10px; border-bottom: 2px solid #e2e8f7;
    }
    .sec-header .sec-title { font-size: 1.05rem; font-weight: 700; color: #1e293b; }
    .activity-strip {
        background: white; border-radius: 12px; padding: 14px 18px; margin-bottom: 20px;
        border-left: 4px solid #1a56db; box-shadow: 0 2px 8px rgba(26,86,219,0.05);
    }
    .activity-strip .act-title {
        font-size: 0.75rem; font-weight: 700; letter-spacing: 1px;
        text-transform: uppercase; color: #1a56db; margin-bottom: 8px;
    }
    .activity-item { font-size: 0.88rem; color: #475569; padding: 3px 0; }
    .activity-item::before { content: "•  "; color: #1a56db; font-weight: 700; }
    .ann-card {
        background: white; border-radius: 12px; padding: 16px 18px; margin-bottom: 10px;
        border: 1px solid #e2e8f7; border-left: 4px solid #1a56db;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }
    .ann-card.urgent { border-left-color: #ef4444; background: #fff8f8; }
    .ann-card.read   { border-left-color: #cbd5e1; opacity: 0.7; }
    .ann-card .ann-badge {
        display: inline-block; padding: 2px 10px; border-radius: 20px;
        font-size: 0.68rem; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 8px;
    }
    .badge-urgent { background: #fee2e2; color: #ef4444; }
    .badge-normal { background: #dbeafe; color: #1a56db; }
    .badge-read   { background: #f1f5f9; color: #94a3b8; }
    .ann-card .ann-text { font-size: 0.9rem; color: #334155; line-height: 1.6; }
    .mat-row {
        background: white; border-radius: 12px; padding: 14px 18px; margin-bottom: 10px;
        border: 1px solid #e2e8f7; display: flex; align-items: center; gap: 14px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .mat-icon {
        width: 44px; height: 44px; border-radius: 10px; background: #dbeafe; color: #1a56db;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.72rem; font-weight: 800; flex-shrink: 0;
    }
    .mat-icon.pdf  { background: #fee2e2; color: #ef4444; }
    .mat-info strong { font-size: 0.9rem; color: #1e293b; display: block; }
    .mat-info span   { font-size: 0.75rem; color: #94a3b8; }
    .member-card {
        background: white; border-radius: 12px; padding: 14px 18px; margin-bottom: 8px;
        border: 1px solid #e2e8f7; display: flex; align-items: center; gap: 14px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .avatar {
        width: 42px; height: 42px; border-radius: 50%; background: #dbeafe; color: #1a56db;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.1rem; font-weight: 800; flex-shrink: 0;
    }
    .avatar.you { background: #1a56db; color: white; }
    .m-name { font-size: 0.92rem; font-weight: 700; color: #1e293b; }
    .m-meta { font-size: 0.75rem; color: #94a3b8; margin-top: 1px; }
    .you-tag {
        display: inline-block; background: #dbeafe; color: #1a56db;
        font-size: 0.65rem; font-weight: 700; padding: 1px 8px;
        border-radius: 10px; margin-left: 6px; vertical-align: middle;
    }
    .group-banner {
        background: linear-gradient(135deg, #1a56db, #0e3fad);
        border-radius: 14px; padding: 22px 24px; margin-bottom: 16px; color: white;
    }
    .group-banner .gb-label { font-size: 0.7rem; letter-spacing: 2px; text-transform: uppercase; opacity: 0.7; margin-bottom: 6px; }
    .group-banner .gb-val   { font-size: 2rem; font-weight: 900; margin-bottom: 4px; }
    .group-banner .gb-sub   { font-size: 0.82rem; opacity: 0.65; }
    .profile-card {
        background: white; border-radius: 16px; padding: 28px;
        border: 1px solid #e2e8f7; box-shadow: 0 4px 16px rgba(26,86,219,0.07);
    }
    .profile-avatar {
        width: 72px; height: 72px; border-radius: 50%;
        background: linear-gradient(135deg, #1a56db, #0e3fad); color: white;
        display: flex; align-items: center; justify-content: center;
        font-size: 2rem; font-weight: 900; margin-bottom: 16px;
    }
    .profile-name { font-size: 1.3rem; font-weight: 800; color: #1e293b; margin-bottom: 4px; }
    .profile-reg  { font-size: 0.82rem; color: #94a3b8; margin-bottom: 16px; }
    .profile-row  {
        display: flex; justify-content: space-between; padding: 10px 0;
        border-bottom: 1px solid #f1f5f9; font-size: 0.88rem;
    }
    .profile-row .pr-label { color: #94a3b8; font-weight: 500; }
    .profile-row .pr-val   { color: #1e293b; font-weight: 700; }
    .msg-info-card {
        background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 12px;
        padding: 14px 18px; margin-bottom: 16px; font-size: 0.88rem;
        color: #1e40af; line-height: 1.6;
    }
    .msg-box {
        border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;
        border: 1px solid rgba(245,158,11,0.25); background: rgba(245,158,11,0.04);
    }
    .msg-from { font-size: 0.78rem; opacity: 0.6; margin-bottom: 4px; }
    .msg-text { font-size: 0.9rem; line-height: 1.5; }
    .pro-divider { height: 1px; background: #e2e8f7; margin: 22px 0; }
    .metric-card {
        background: white; border-radius: 14px; padding: 18px 14px; text-align: center;
        border: 1px solid #e2e8f7; box-shadow: 0 2px 8px rgba(26,86,219,0.06); margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)


def metric_card(title, value, icon):
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:1.6rem;margin-bottom:6px;">{icon}</div>
        <div style="font-size:1.35rem;font-weight:800;color:#1a56db;margin-bottom:4px;">{value}</div>
        <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;font-weight:600;">{title}</div>
    </div>
    """, unsafe_allow_html=True)


def render_student_interface(db: SheetDatabaseManager, ai_study, df_profiles):
    inject_css()

    st.title("📋 Student Portal")
    st.markdown("---")

    # ── Session state initialization ─────────────────────────
    if "student_logged_in"    not in st.session_state: st.session_state.student_logged_in    = None
    if "show_reg_form"        not in st.session_state: st.session_state.show_reg_form        = False
    if "read_announcements"   not in st.session_state: st.session_state.read_announcements   = []
    if "student_tab"          not in st.session_state: st.session_state.student_tab          = "🏠 Home"
    if "go_to_home"           not in st.session_state: st.session_state.go_to_home           = False
    if "show_ai_tab"          not in st.session_state: st.session_state.show_ai_tab          = False
    if "open_expanders"       not in st.session_state: st.session_state.open_expanders       = {}
    if "confirm_clear_all"    not in st.session_state: st.session_state.confirm_clear_all    = False
    if "ai_chat_history"      not in st.session_state: st.session_state.ai_chat_history      = []
    if "ai_pdf_text"          not in st.session_state: st.session_state.ai_pdf_text          = ""
    if "ai_selected_file"     not in st.session_state: st.session_state.ai_selected_file     = ""
    if "ai_summary_shown"     not in st.session_state: st.session_state.ai_summary_shown     = False

    # ─────────────────────────────────────────
    # Login
    # ─────────────────────────────────────────
    if not st.session_state.student_logged_in and not st.session_state.show_reg_form:
        st.subheader("🔑 Student Account Login")
        login_reg = st.text_input("Enter Your Registration Number:", placeholder="e.g., 25/U/0000/PS").strip().upper()
        col1, col2 = st.columns(2)
        with col1: login_btn = st.button("🔓 Log In")
        with col2: register_toggle_btn = st.button("📝 Register New Account")

        if register_toggle_btn:
            st.session_state.show_reg_form = True
            st.rerun()
        if login_btn:
            if not login_reg:
                st.warning("Please enter your Registration Number.")
            elif not df_profiles.empty and login_reg in df_profiles['Reg Number'].astype(str).values:
                st.session_state.student_logged_in = login_reg
                st.session_state.show_reg_form     = False
                st.rerun()
            else:
                st.error(f"❌ Account '{login_reg}' not found.")

    # ─────────────────────────────────────────
    # Registration
    # ─────────────────────────────────────────
    if st.session_state.show_reg_form:
        st.subheader("📝 Create New Student Account")
        with st.form("register_form", clear_on_submit=True):
            name    = st.text_input("Full Name", placeholder="e.g., Obema Kelly")
            reg     = st.text_input("Registration Number", placeholder="25/U/0000/PS").strip().upper()
            code    = st.selectbox("Course Code", ["BMEC", "BBPE", "BWIE", "BAGE"], index=0)
            contact = st.text_input("Contact Info", placeholder="e.g., 074421539")
            submit_reg = st.form_submit_button("✅ Register")
            if submit_reg:
                if not name or not reg:
                    st.warning("Name and Registration Number are required.")
                else:
                    if db.register_student(name, reg, code, contact):
                        st.session_state.show_reg_form = False
                        st.rerun()
                    else:
                        st.error("⚠️ Registration failed. Please try again.")
        if st.button("← Back to Login"):
            st.session_state.show_reg_form = False
            st.rerun()

    # ─────────────────────────────────────────
    # Logged-in View
    # ─────────────────────────────────────────
    if st.session_state.student_logged_in:
        student_data = df_profiles[df_profiles["Reg Number"] == st.session_state.student_logged_in].iloc[0]

        s_name   = student_data["Student Name"]
        s_reg    = st.session_state.student_logged_in                   # ✅ defined first
        s_course = student_data.get("Course Code", "N/A")
        s_group  = student_data.get("Assigned Group", "Not Assigned")

        announcements  = db.fetch_announcements()
        materials_list = db.fetch_materials()
        my_rep_replies    = db.fetch_rep_replies(reg_number=s_reg)      # ✅ now works
        unread_rep_count  = sum(1 for r in my_rep_replies if r.get("read_status", "Unread").lower() == "unread")

        # Count unread
        unread = []
        urgent_unread = []
        for ann in announcements:
            ann_id = ann.get("id", ann.get("text", ""))[:20] if isinstance(ann, dict) else str(ann)[:20]
            if ann_id not in st.session_state.read_announcements:
                unread.append(ann)
                if isinstance(ann, dict) and ann.get("priority", "").lower() == "urgent":
                    urgent_unread.append(ann)

        unread_count  = len(unread)
        new_materials = len(materials_list)

        # Welcome Banner
        st.markdown(f"""
        <div class="welcome-banner">
            <div class="wb-label">MEC Student Portal</div>
            <h2>👋 Welcome back, {s_name}!</h2>
            <p>Stay updated with notices, materials and class activities.</p>
            <div class="pill-strip">
                <span class="pill">🎓 {s_reg}</span>
                <span class="pill">📘 {s_course}</span>
                <span class="pill">👥 {s_group}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Activity Strip
        activity_items = ""
        if unread_count:
            activity_items += f'<div class="activity-item">{unread_count} unread announcement(s)</div>'
        if new_materials:
            activity_items += f'<div class="activity-item">{new_materials} material(s) available</div>'
        if unread_rep_count:
            activity_items += f'<div class="activity-item">{unread_rep_count} new reply/replies from Class Rep</div>'
        if activity_items:
            st.markdown(f'<div class="activity-strip"><div class="act-title">🔔 Recent Activity</div>{activity_items}</div>', unsafe_allow_html=True)
        else:
            st.success("✅ Everything is up to date.")

        # Tab Navigation
        tabs = ["🏠 Home", "🔔 Notices", "📚 Materials", "👥 My Group", "✉️ Message", "💬 Rep Replies", "👤 Profile", "🤖 AI Assistant"]
        tab_labels = []
        for t in tabs:
            if t == "🔔 Notices" and unread_count > 0:
                tab_labels.append(f"🔔 Notices ({unread_count})")
            elif t == "💬 Rep Replies" and unread_rep_count > 0:
                tab_labels.append(f"💬 Rep Replies ({unread_rep_count})")
            else:
                tab_labels.append(t)

        default_tab_index = 0
        if st.session_state.go_to_home:
            st.session_state.go_to_home = False
            default_tab_index = 0

        selected_tab = st.radio("Navigate", tab_labels, horizontal=True, label_visibility="collapsed", key="student_nav", index=default_tab_index)
        active_tab   = selected_tab.split(" (")[0]
        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        # ════════════════════════════════════════
        # 🏠 HOME
        # ════════════════════════════════════════
        if active_tab == "🏠 Home":
            col1, col2, col3, col4 = st.columns(4)
            with col1: metric_card("Unread Notices", unread_count, "🔔")
            with col2: metric_card("Materials", new_materials, "📚")
            with col3: metric_card("Group", s_group, "👥")
            with col4: metric_card("Course", s_course, "🎓")
            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            if urgent_unread:
                st.markdown('<div class="sec-header"><span class="sec-title">🚨 Urgent — Action Required</span></div>', unsafe_allow_html=True)
                for uidx, ann in enumerate(urgent_unread):
                    ann_text = ann.get("text", str(ann)) if isinstance(ann, dict) else str(ann)
                    ann_id   = ann.get("id", ann_text[:20]) if isinstance(ann, dict) else ann_text[:20]
                    st.markdown(f'<div class="ann-card urgent"><span class="ann-badge badge-urgent">🚨 URGENT</span><div class="ann-text">{ann_text}</div></div>', unsafe_allow_html=True)
                    if st.button("✅ Mark as Read", key=f"home_read_{uidx}_{ann_id}"):
                        st.session_state.read_announcements.append(ann_id)
                        st.success("✅ Marked as read.")
                st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            normal_unread = [a for a in unread if a not in urgent_unread]
            if normal_unread:
                st.markdown('<div class="sec-header"><span class="sec-title">📢 Latest Notice</span></div>', unsafe_allow_html=True)
                ann      = normal_unread[0]
                ann_text = ann.get("text", str(ann)) if isinstance(ann, dict) else str(ann)
                st.markdown(f'<div class="ann-card"><span class="ann-badge badge-normal">NOTICE</span><div class="ann-text">{ann_text}</div></div>', unsafe_allow_html=True)
                if len(normal_unread) > 1:
                    st.caption(f"+ {len(normal_unread) - 1} more unread in Notices tab")

            if not urgent_unread and not normal_unread:
                st.success("✅ You're all caught up! No unread notices.")

        # ════════════════════════════════════════
        # 🔔 NOTICES
        # ════════════════════════════════════════
        elif active_tab == "🔔 Notices":
            st.markdown('<div class="sec-header"><span class="sec-title">🔔 Noticeboard</span></div>', unsafe_allow_html=True)
            if unread_count > 0:
                st.warning(f"You have **{unread_count} unread** announcement(s)")
            if announcements:
                for idx, ann in enumerate(announcements):
                    ann_text = ann.get("text", str(ann)) if isinstance(ann, dict) else str(ann)
                    ann_id   = ann.get("id", ann_text[:20]) if isinstance(ann, dict) else ann_text[:20]
                    priority = ann.get("priority", "normal").lower() if isinstance(ann, dict) else "normal"
                    is_read  = ann_id in st.session_state.read_announcements
                    if ann_id not in st.session_state.open_expanders:
                        st.session_state.open_expanders[ann_id] = not is_read
                    card_class  = "urgent" if priority == "urgent" and not is_read else ("read" if is_read else "")
                    badge_class = "badge-urgent" if priority == "urgent" else ("badge-read" if is_read else "badge-normal")
                    badge_label = "🚨 URGENT" if priority == "urgent" else ("✅ READ" if is_read else "NOTICE")
                    with st.expander(f"{'✅' if is_read else '🔴' if priority == 'urgent' else '🟡'} {ann_text[:55]}..."):
                        st.markdown(f'<div class="ann-card {card_class}" style="margin:0;"><span class="ann-badge {badge_class}">{badge_label}</span><div class="ann-text">{ann_text}</div></div>', unsafe_allow_html=True)
                        if not is_read:
                            if st.checkbox("✅ Mark as Read", key=f"notice_read_{idx}_{ann_id}"):
                                if ann_id not in st.session_state.read_announcements:
                                    st.session_state.read_announcements.append(ann_id)
                                st.session_state.open_expanders[ann_id] = True
                        else:
                            st.caption("✅ Read")
            else:
                st.info("No announcements yet.")

        # ════════════════════════════════════════
        # 📚 MATERIALS
        # ════════════════════════════════════════
        elif active_tab == "📚 Materials":
            st.markdown('<div class="sec-header"><span class="sec-title">📚 Course Materials</span></div>', unsafe_allow_html=True)
            search = st.text_input("🔍 Search Materials", placeholder="Search by file name...")
            filtered = [i for i in materials_list if search.lower() in (i.get("name","") if isinstance(i,dict) else str(i)).lower()]
            if filtered:
                for item in filtered:
                    file_name = item.get("name","Unnamed File") if isinstance(item,dict) else (item[0] if isinstance(item,list) else "Unnamed File")
                    file_url  = item.get("url","#")            if isinstance(item,dict) else (item[1] if isinstance(item,list) else "#")
                    ext       = file_name.split(".")[-1].upper() if "." in file_name else "FILE"
                    icon_cls  = "pdf" if ext == "PDF" else "docx"
                    st.markdown(f'<div class="mat-row"><div class="mat-icon {icon_cls}">{ext}</div><div class="mat-info"><strong>{file_name}</strong><span>Tap download to save to your device</span></div></div>', unsafe_allow_html=True)
                    file_data = db.fetch_file_bytes(file_url)
                    if file_data:
                        st.download_button("⬇️ Download", data=file_data, file_name=file_name, mime="application/pdf", key=f"dl_{file_name}")
                    else:
                        st.warning("⚠️ File unavailable")
            else:
                st.info("No study materials distributed yet.")

        # ════════════════════════════════════════
        # 👥 MY GROUP
        # ════════════════════════════════════════
        elif active_tab == "👥 My Group":
            st.markdown('<div class="sec-header"><span class="sec-title">👥 Project Group</span></div>', unsafe_allow_html=True)
            team_status = student_data.get("Assigned Group", None)
            if not team_status or str(team_status).strip() == "" or str(team_status).strip() == "Unassigned":
                st.warning("⏳ You have not been assigned a group yet.")
            else:
                group_members = df_profiles[df_profiles["Assigned Group"] == team_status]
                st.markdown(f'<div class="group-banner"><div class="gb-label">Assigned Group</div><div class="gb-val">{team_status}</div><div class="gb-sub">{len(group_members)} member(s) · {s_course}</div></div>', unsafe_allow_html=True)
                if not group_members.empty:
                    st.markdown('<div class="sec-header" style="margin-top:8px;"><span class="sec-title">Group Members</span></div>', unsafe_allow_html=True)
                    for _, member in group_members.iterrows():
                        m_name   = member["Student Name"]
                        m_reg    = member["Reg Number"]
                        m_course = member["Course Code"]
                        initial  = m_name[0].upper() if m_name else "?"
                        is_you   = (m_reg == s_reg)
                        you_html = '<span class="you-tag">You</span>' if is_you else ""
                        av_cls   = "avatar you" if is_you else "avatar"
                        st.markdown(f'<div class="member-card"><div class="{av_cls}">{initial}</div><div><div class="m-name">{m_name}{you_html}</div><div class="m-meta">{m_course} · {m_reg}</div></div></div>', unsafe_allow_html=True)
                else:
                    st.warning("No members found in your group yet.")

        # ════════════════════════════════════════
        # ✉️ MESSAGE
        # ════════════════════════════════════════
        elif active_tab == "✉️ Message":
            st.markdown('<div class="sec-header"><span class="sec-title">📬 Message Class Rep</span></div>', unsafe_allow_html=True)
            st.markdown('<div class="msg-info-card">🔒 <strong>Private & Confidential</strong> — Only your Class Representatives can see your message.</div>', unsafe_allow_html=True)

            all_feedback = db.fetch_feedback()
            my_messages  = [m for m in all_feedback if isinstance(m, list) and len(m) >= 5 and str(m[1]).strip().lower() == s_reg.strip().lower()]

            if my_messages:
                st.markdown('<div class="sec-header" style="margin-top:8px;"><span class="sec-title">📤 Your Sent Messages</span></div>', unsafe_allow_html=True)
                col_a, col_b = st.columns([3, 1])
                with col_b:
                    if not st.session_state.confirm_clear_all:
                        if st.button("🗑️ Clear All", key="clear_all_btn"):
                            st.session_state.confirm_clear_all = True
                            st.rerun()
                if st.session_state.confirm_clear_all:
                    st.warning("⚠️ This will permanently delete **all your messages** from the rep inbox. Are you sure?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Yes, delete all", key="confirm_yes"):
                            with st.spinner("Deleting..."):
                                if db.delete_all_feedback(s_reg):
                                    st.session_state.confirm_clear_all = False
                                    st.success("🗑️ All messages deleted.")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed.")
                    with c2:
                        if st.button("❌ Cancel", key="confirm_no"):
                            st.session_state.confirm_clear_all = False
                            st.rerun()

                for midx, msg in enumerate(my_messages):
                    timestamp    = str(msg[0])
                    status       = str(msg[3])
                    msg_text     = str(msg[4])
                    status_color = "#16a34a" if status.lower() == "reviewed" else "#d4820a"
                    st.markdown(f'<div class="msg-box"><div class="msg-from">🕐 {timestamp} &nbsp;·&nbsp; <span style="color:{status_color};font-weight:600;">{status}</span></div><div class="msg-text">{msg_text}</div></div>', unsafe_allow_html=True)
                    if st.button("🗑️ Delete", key=f"del_msg_{midx}_{timestamp[:10]}"):
                        with st.spinner("Deleting..."):
                            if db.delete_feedback(timestamp, s_reg):
                                st.success("✅ Message deleted.")
                                st.rerun()
                            else:
                                st.error("❌ Could not delete.")
                st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            st.markdown('<div class="sec-header"><span class="sec-title">✏️ New Message</span></div>', unsafe_allow_html=True)
            with st.form("student_feedback_form", clear_on_submit=True):
                user_msg  = st.text_area("Type your message here:", placeholder="e.g., Hello Rep, I have an issue with my group...", key="st_fb_area", height=140)
                submit_fb = st.form_submit_button("✉️ Send Private Message")
                if submit_fb:
                    if user_msg.strip():
                        with st.spinner("Sending..."):
                            if db.submit_feedback(s_reg, s_name, user_msg):
                                cached_fetch_feedback.clear()
                                st.success("🚀 Message delivered!")
                                st.rerun()
                            else:
                                st.error("❌ Submission failed.")
                    else:
                        st.warning("Please type a message before sending.")

        # ════════════════════════════════════════
        # 💬 REP REPLIES
        # ════════════════════════════════════════
        elif active_tab == "💬 Rep Replies":
            st.markdown('<div class="sec-header"><span class="sec-title">💬 Messages from Class Rep</span></div>', unsafe_allow_html=True)

            if unread_rep_count > 0:
                st.info(f"📬 You have **{unread_rep_count} unread** message(s) from your Class Rep.")
            elif my_rep_replies:
                st.success("✅ All messages read.")

            if my_rep_replies:
                for ridx, reply in enumerate(my_rep_replies):
                    r_time   = reply.get("timestamp", "N/A")
                    r_rep    = reply.get("rep_name", "Class Rep")
                    r_msg    = reply.get("message", "")
                    r_status = reply.get("read_status", "Unread")
                    is_read  = r_status.lower() == "read"

                    left_col   = "#16a34a" if is_read else "#3b82f6"
                    card_bg    = "#f0fdf4" if is_read else "#eff6ff"
                    border_col = "#86efac" if is_read else "#93c5fd"
                    read_label = "👁️ Read" if is_read else "🔵 New"
                    new_badge  = "" if is_read else '<span style="background:#3b82f6;color:white;font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:10px;margin-left:6px;">NEW</span>'

                    st.markdown(f"""
                    <div style="background:{card_bg};border:1px solid {border_col};
                        border-left:4px solid {left_col};border-radius:12px;
                        padding:14px 18px;margin-bottom:10px;">
                        <div style="font-size:0.75rem;color:#64748b;margin-bottom:6px;">
                            👑 <strong>{r_rep}</strong>{new_badge} &nbsp;·&nbsp; 🕐 {r_time}
                            &nbsp;·&nbsp; <span style="color:{left_col};font-weight:600;">{read_label}</span>
                        </div>
                        <div style="font-size:0.92rem;color:#1e293b;line-height:1.6;">{r_msg}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if not is_read:
                        if st.button("✅ Mark as Read", key=f"rep_read_{ridx}_{r_time[:10]}"):
                            with st.spinner("Marking as read..."):
                                ok = db.mark_rep_reply_read(timestamp=r_time, reg_number=s_reg)
                            if ok:
                                cached_fetch_rep_replies.clear()
                                st.rerun()
                            else:
                                st.error("❌ Could not update. Please try again.")
                    st.markdown('<div style="margin-bottom:4px;"></div>', unsafe_allow_html=True)
            else:
                st.info("No messages from your Class Rep yet.")

        # ════════════════════════════════════════
        # 👤 PROFILE
        # ════════════════════════════════════════
        elif active_tab == "👤 Profile":
            st.markdown('<div class="sec-header"><span class="sec-title">👤 Student Profile</span></div>', unsafe_allow_html=True)
            initial = s_name[0].upper() if s_name else "?"
            st.markdown(f"""
            <div class="profile-card">
                <div class="profile-avatar">{initial}</div>
                <div class="profile-name">{s_name}</div>
                <div class="profile-reg">{s_reg}</div>
                <div class="profile-row"><span class="pr-label">Course Code</span><span class="pr-val">{s_course}</span></div>
                <div class="profile-row"><span class="pr-label">Assigned Group</span><span class="pr-val">{s_group}</span></div>
                <div class="profile-row" style="border-bottom:none;"><span class="pr-label">Status</span><span class="pr-val" style="color:#16a34a;">✅ Active</span></div>
            </div>
            """, unsafe_allow_html=True)

        # ════════════════════════════════════════
        # 🤖 AI ASSISTANT
        # ════════════════════════════════════════
        elif active_tab == "🤖 AI Assistant":
            from ai_engine import extract_pdf_text

            if not st.session_state.show_ai_tab:
                # ── Closed: show start screen ────────
                st.markdown("""
                <div class="welcome-banner" style="text-align:center;">
                    <div style="font-size:2.5rem;margin-bottom:10px;">🤖</div>
                    <h2 style="margin:0 0 8px 0;">AI Study Assistant</h2>
                    <p style="margin:0 0 16px 0;">Ask academic questions or select a course material for AI to summarize and explain it.</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("▶ Start AI Assistant", use_container_width=True, key="start_ai_btn"):
                    st.session_state.show_ai_tab = True
                    st.rerun()
            else:
                # ── Open: full chat ──────────────────
                col_title, col_close = st.columns([4, 1])
                with col_title:
                    st.markdown('<div class="sec-header"><span class="sec-title">🤖 AI Study Assistant</span></div>', unsafe_allow_html=True)
                with col_close:
                    if st.button("✖ Close", key="close_ai_btn", use_container_width=True):
                        st.session_state.ai_chat_history  = []
                        st.session_state.ai_summary_shown = False
                        st.session_state.ai_pdf_text      = ""
                        st.session_state.ai_selected_file = ""
                        st.session_state.show_ai_tab      = False
                        st.rerun()

                st.markdown('<div class="msg-info-card">💡 Ask any academic question, or select a course material for the AI to read and summarize.</div>', unsafe_allow_html=True)

                # Material selector
                mat_names    = ["— No material (general Q&A) —"] + [m.get("name","Unnamed") for m in materials_list]
                selected_name = st.selectbox("📄 Select a course material (optional):", mat_names, key="ai_mat_select")

                if selected_name != "— No material (general Q&A) —":
                    sel_mat   = next((m for m in materials_list if m.get("name") == selected_name), None)
                    if sel_mat:
                        file_url  = sel_mat.get("url", "")
                        file_name = sel_mat.get("name", "")
                        if st.session_state.ai_selected_file != file_name:
                            st.session_state.ai_selected_file = file_name
                            st.session_state.ai_summary_shown = False
                            st.session_state.ai_chat_history  = []
                            with st.spinner("📖 Reading material..."):
                                st.session_state.ai_pdf_text = extract_pdf_text(file_url, file_name)
                        if not st.session_state.ai_summary_shown:
                            with st.spinner("✍️ Generating summary..."):
                                summary = ai_study.summarize_material(st.session_state.ai_pdf_text, file_name, student_reg=s_reg)
                            st.markdown(f'<div class="ann-card" style="margin-bottom:16px;"><span class="ann-badge badge-normal">📋 SUMMARY</span><div class="ann-text">{summary}</div></div>', unsafe_allow_html=True)
                            st.session_state.ai_summary_shown = True
                            st.session_state.ai_chat_history.append({"role": "assistant", "content": f"Summary of {file_name}:\n{summary}"})
                else:
                    if st.session_state.ai_selected_file != "":
                        st.session_state.ai_selected_file = ""
                        st.session_state.ai_pdf_text      = ""
                        st.session_state.ai_summary_shown = False
                        st.session_state.ai_chat_history  = []

                st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

                # Chat history
                for turn in st.session_state.ai_chat_history:
                    if turn["role"] == "user":
                        st.markdown(f'<div style="background:#dbeafe;border-radius:10px;padding:10px 14px;margin-bottom:8px;margin-left:20%;text-align:right;"><div style="font-size:0.78rem;color:#1e40af;font-weight:600;margin-bottom:4px;">You</div><div style="font-size:0.9rem;color:#1e293b;">{turn["content"]}</div></div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div style="background:white;border:1px solid #e2e8f7;border-radius:10px;padding:10px 14px;margin-bottom:8px;margin-right:20%;"><div style="font-size:0.78rem;color:#1a56db;font-weight:600;margin-bottom:4px;">🤖 AI Assistant</div><div style="font-size:0.9rem;color:#1e293b;line-height:1.6;">{turn["content"]}</div></div>', unsafe_allow_html=True)

                # Question input
                placeholder = f"Ask about {st.session_state.ai_selected_file}..." if st.session_state.ai_selected_file else "Ask any academic question e.g. Explain Newton's second law..."
                with st.form("ai_chat_form", clear_on_submit=True):
                    user_question = st.text_area("Your question:", placeholder=placeholder, height=90, key="ai_question_input", label_visibility="collapsed")
                    c1, c2 = st.columns([3, 1])
                    with c1: send_btn  = st.form_submit_button("📨 Ask AI", use_container_width=True)
                    with c2: clear_btn = st.form_submit_button("🗑️ Clear",  use_container_width=True)

                    if send_btn and user_question.strip():
                        with st.spinner("🤖 Thinking..."):
                            answer = ai_study.ask_ai(
                                question     = user_question.strip(),
                                chat_history = st.session_state.ai_chat_history,
                                pdf_text     = st.session_state.ai_pdf_text,
                                file_name    = st.session_state.ai_selected_file,
                                student_reg  = s_reg
                            )
                        st.session_state.ai_chat_history.append({"role": "user",      "content": user_question.strip()})
                        st.session_state.ai_chat_history.append({"role": "assistant", "content": answer})
                        st.rerun()

                    if clear_btn:
                        st.session_state.ai_chat_history  = []
                        st.session_state.ai_summary_shown = False
                        st.rerun()

        # ── Logout ───────────────────────────────
        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
        if st.button("🔒 Log Out"):
            for key in ["student_logged_in", "student_tab", "read_announcements",
                        "open_expanders", "show_ai_tab", "ai_chat_history",
                        "ai_pdf_text", "ai_selected_file", "ai_summary_shown",
                        "confirm_clear_all", "go_to_home"]:
                if key in st.session_state:
                    del st.session_state[key]
            # Clear any per-student AI cooldown keys
            keys_to_delete = [k for k in st.session_state if k.startswith("ai_last_request_")]
            for k in keys_to_delete:
                del st.session_state[k]
            st.rerun()