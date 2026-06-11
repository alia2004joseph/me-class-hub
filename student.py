"""
student.py — Student Portal UI.
Read receipts removed. Dept+year scoped. Coloured themes per department.
"""
import streamlit as st
from database import SheetDatabaseManager
from cache import cached_fetch_feedback, cached_fetch_rep_replies
from config import (
    DEPARTMENTS, YEARS, DEPT_CODES,
    dept_color, dept_light, dept_name, dept_courses
)


def inject_css(primary: str = "#1a56db", light: str = "#dbeafe"):
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    html,body,[class*="css"]{{font-family:'Plus Jakarta Sans',sans-serif;}}
    #MainMenu,footer{{visibility:hidden;}}
    .stApp{{background:#F0F4FF;}}
    .welcome-banner{{
        background:linear-gradient(135deg,{primary} 0%,{primary}cc 100%);
        border-radius:18px;padding:28px 32px;margin-bottom:24px;color:white;
    }}
    .welcome-banner h2{{font-size:1.7rem;font-weight:800;margin:0 0 6px 0;color:white;}}
    .welcome-banner p{{font-size:0.88rem;opacity:0.75;margin:0 0 14px 0;}}
    .pill-strip{{display:flex;flex-wrap:wrap;gap:8px;margin-top:4px;}}
    .pill{{
        background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.25);
        border-radius:20px;padding:4px 14px;font-size:0.75rem;font-weight:600;color:white;
    }}
    .stat-card{{
        background:white;border-radius:14px;padding:18px 14px;text-align:center;
        border:1px solid #e2e8f7;box-shadow:0 2px 8px rgba(0,0,0,0.06);
    }}
    .stat-card .s-val{{font-size:1.45rem;font-weight:800;color:{primary};}}
    .stat-card .s-label{{font-size:0.7rem;color:#94a3b8;text-transform:uppercase;font-weight:600;}}
    .ann-card{{
        background:white;border-radius:12px;padding:16px 18px;margin-bottom:10px;
        border:1px solid #e2e8f7;border-left:4px solid {primary};
    }}
    .ann-card.urgent{{border-left-color:#ef4444;background:#fff8f8;}}
    .ann-card.read{{border-left-color:#cbd5e1;opacity:0.7;}}
    .ann-badge{{display:inline-block;padding:2px 10px;border-radius:20px;
        font-size:0.68rem;font-weight:700;margin-bottom:8px;}}
    .badge-normal{{background:{light};color:{primary};}}
    .badge-urgent{{background:#fee2e2;color:#ef4444;}}
    .badge-read{{background:#f1f5f9;color:#94a3b8;}}
    .mat-row{{
        background:white;border-radius:12px;padding:14px 18px;margin-bottom:10px;
        border:1px solid #e2e8f7;display:flex;align-items:center;gap:14px;
    }}
    .mat-icon{{width:44px;height:44px;border-radius:10px;background:{light};color:{primary};
        display:flex;align-items:center;justify-content:center;font-size:0.72rem;font-weight:800;}}
    .mat-icon.pdf{{background:#fee2e2;color:#ef4444;}}
    .member-card{{
        background:white;border-radius:12px;padding:14px 18px;margin-bottom:8px;
        border:1px solid #e2e8f7;display:flex;align-items:center;gap:14px;
    }}
    .avatar{{width:42px;height:42px;border-radius:50%;background:{light};color:{primary};
        display:flex;align-items:center;justify-content:center;font-size:1.1rem;font-weight:800;}}
    .avatar.you{{background:{primary};color:white;}}
    .group-banner{{
        background:linear-gradient(135deg,{primary},{primary}cc);
        border-radius:14px;padding:22px 24px;margin-bottom:16px;color:white;
    }}
    .profile-card{{
        background:white;border-radius:16px;padding:28px;
        border:1px solid #e2e8f7;box-shadow:0 4px 16px rgba(0,0,0,0.07);
    }}
    .profile-avatar{{
        width:72px;height:72px;border-radius:50%;
        background:linear-gradient(135deg,{primary},{primary}cc);color:white;
        display:flex;align-items:center;justify-content:center;
        font-size:2rem;font-weight:900;margin-bottom:16px;
    }}
    .msg-info-card{{
        background:{light};border:1px solid {primary}44;border-radius:12px;
        padding:14px 18px;margin-bottom:16px;font-size:0.88rem;color:{primary};
    }}
    .pro-divider{{height:1px;background:#e2e8f7;margin:22px 0;}}
    .metric-card{{
        background:white;border-radius:14px;padding:18px 14px;text-align:center;
        border:1px solid #e2e8f7;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:10px;
    }}
    .activity-strip{{
        background:white;border-radius:12px;padding:14px 18px;margin-bottom:20px;
        border-left:4px solid {primary};
    }}
    /* Pill-style tabs */
    .stTabs [data-baseweb="tab-list"]{{
        gap:4px;background:white;border-radius:12px;padding:4px;
        border:1px solid #e2e8f7;flex-wrap:wrap;
    }}
    .stTabs [data-baseweb="tab"]{{
        border-radius:8px;padding:8px 16px;font-weight:600;
        font-size:0.82rem;color:#64748b;background:transparent;border:none;
    }}
    .stTabs [aria-selected="true"]{{background:{primary} !important;color:white !important;}}
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"]{{display:none;}}
    </style>
    """, unsafe_allow_html=True)


def metric_card(title, value, icon, color="#1a56db"):
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:1.6rem;margin-bottom:6px;">{icon}</div>
        <div style="font-size:1.35rem;font-weight:800;color:{color};margin-bottom:4px;">{value}</div>
        <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;font-weight:600;">{title}</div>
    </div>
    """, unsafe_allow_html=True)


def render_student_interface(db: SheetDatabaseManager, ai_study, df_profiles):

    # ── Session init ──────────────────────────────────────────
    defaults = {
        "student_logged_in":  None,
        "show_reg_form":      False,
        "read_announcements": [],
        "go_to_home":         False,
        "show_ai_tab":        False,
        "open_expanders":     {},
        "confirm_clear_all":  False,
        "ai_chat_history":    [],
        "ai_pdf_text":        "",
        "ai_selected_file":   "",
        "ai_summary_shown":   False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ── Default theme (blue) until logged in ─────────────────
    primary = "#1a56db"
    light   = "#dbeafe"

    if st.session_state.student_logged_in and not df_profiles.empty:
        row = df_profiles[df_profiles["Reg Number"] == st.session_state.student_logged_in]
        if not row.empty:
            d_col = next((c for c in ["Department","department","dept"]
                          if c in row.columns), None)
            if d_col:
                d = str(row.iloc[0][d_col])
                primary = dept_color(d)
                light   = dept_light(d)

    inject_css(primary, light)
    st.title("📋 Student Portal")
    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # LOGIN
    # ════════════════════════════════════════════════════════
    if not st.session_state.student_logged_in and not st.session_state.show_reg_form:
        st.subheader("🔑 Student Login")
        login_reg = st.text_input(
            "Registration Number", placeholder="e.g., 25/U/0000/PS"
        ).strip().upper()
        c1, c2 = st.columns(2)
        with c1: login_btn = st.button("🔓 Log In")
        with c2: reg_btn   = st.button("📝 Register New Account")

        if reg_btn:
            st.session_state.show_reg_form = True
            st.rerun()
        if login_btn:
            if not login_reg:
                st.warning("Please enter your Registration Number.")
            elif not df_profiles.empty and \
                 login_reg in df_profiles["Reg Number"].astype(str).values:
                st.session_state.student_logged_in = login_reg
                st.rerun()
            else:
                st.error(f"❌ '{login_reg}' not found. Please register first.")

    # ════════════════════════════════════════════════════════
    # REGISTRATION
    # ════════════════════════════════════════════════════════
    if st.session_state.show_reg_form:
        st.subheader("📝 Create New Student Account")

        # Dept + Year + Course OUTSIDE the form so course codes update instantly
        dept_options  = {f"{v['name']} ({k})": k for k, v in DEPARTMENTS.items()}
        dept_label    = st.selectbox("Department",    list(dept_options.keys()), key="reg_dept_select")
        selected_dept = dept_options[dept_label]
        year          = st.selectbox("Year of Study", YEARS,                     key="reg_year_select")
        courses       = dept_courses(selected_dept)
        code          = st.selectbox("Course Code",   courses,                   key="reg_course_select")

        with st.form("register_form", clear_on_submit=True):
            name    = st.text_input("Full Name",          placeholder="e.g., Obema Kelly")
            reg     = st.text_input("Registration Number",placeholder="25/U/0000/PS").strip().upper()
            contact = st.text_input("Contact Info",       placeholder="e.g., 074421539")
            submit  = st.form_submit_button("✅ Register")

            if submit:
                if not name or not reg:
                    st.warning("Name and Registration Number are required.")
                else:
                    ok = db.register_student(
                        name=name, reg=reg, code=code,
                        contact=contact, dept=selected_dept, year=year
                    )
                    if ok:
                        st.success("✅ Account created! Please log in.")
                        st.session_state.show_reg_form = False
                        st.rerun()
                    else:
                        st.error("⚠️ Registration failed. Please try again.")

        if st.button("← Back to Login"):
            st.session_state.show_reg_form = False
            st.rerun()

    # ════════════════════════════════════════════════════════
    # LOGGED-IN VIEW
    # ════════════════════════════════════════════════════════
    if not st.session_state.student_logged_in:
        return

    if df_profiles.empty or \
       st.session_state.student_logged_in not in df_profiles["Reg Number"].values:
        st.error("❌ Could not load your profile. Please try again.")
        st.stop()

    student_data = df_profiles[
        df_profiles["Reg Number"] == st.session_state.student_logged_in
    ].iloc[0]

    s_name   = student_data["Student Name"]
    s_reg    = st.session_state.student_logged_in
    s_course = student_data.get("Course Code",    "N/A")
    s_group  = student_data.get("Assigned Group", "Not Assigned")

    # Resolve dept + year from any column naming
    s_dept = str(next(
        (student_data.get(c) for c in ["Department","department","dept"]
         if student_data.get(c)), "MEC"
    ))
    s_year = str(next(
        (student_data.get(c) for c in ["Year","year"] if student_data.get(c)), "Year 1"
    ))
    s_dept_name = dept_name(s_dept)
    primary     = dept_color(s_dept)
    light       = dept_light(s_dept)

    # ── Fetch scoped data ─────────────────────────────────────
    dept_anns   = db.fetch_announcements(dept=s_dept, year=s_year)
    global_anns = db.fetch_announcements(dept="ALL",  year="ALL")
    all_anns    = dept_anns + [a for a in global_anns if a not in dept_anns]

    materials_list   = db.fetch_materials(dept=s_dept, year=s_year)
    my_rep_replies   = db.fetch_rep_replies(reg_number=s_reg, dept=s_dept, year=s_year)
    unread_rep_count = sum(
        1 for r in my_rep_replies
        if r.get("read_status", "Unread").lower() == "unread"
    )

    # Count unread announcements (client-side only, no server round-trip)
    unread        = []
    urgent_unread = []
    for ann in all_anns:
        ann_id = (ann.get("id", ann.get("text",""))[:20]
                  if isinstance(ann, dict) else str(ann)[:20])
        if ann_id not in st.session_state.read_announcements:
            unread.append(ann)
            if isinstance(ann, dict) and ann.get("priority","").lower() == "urgent":
                urgent_unread.append(ann)
    unread_count = len(unread)

    # ── Welcome Banner ────────────────────────────────────────
    st.markdown(f"""
    <div class="welcome-banner">
        <div style="font-size:0.72rem;letter-spacing:2px;text-transform:uppercase;
            opacity:0.7;margin-bottom:6px;">{s_dept_name} · {s_year}</div>
        <h2>👋 Welcome back, {s_name}!</h2>
        <p>Stay updated with notices, materials and class activities.</p>
        <div class="pill-strip">
            <span class="pill">🎓 {s_reg}</span>
            <span class="pill">📘 {s_course}</span>
            <span class="pill">👥 {s_group}</span>
            <span class="pill">🏛️ {s_dept}</span>
            <span class="pill">📅 {s_year}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Activity Strip ────────────────────────────────────────
    items = ""
    if unread_count:
        items += f'<div style="font-size:0.88rem;color:#475569;padding:3px 0;">• &nbsp;{unread_count} unread announcement(s)</div>'
    if materials_list:
        items += f'<div style="font-size:0.88rem;color:#475569;padding:3px 0;">• &nbsp;{len(materials_list)} material(s) available</div>'
    if unread_rep_count:
        items += f'<div style="font-size:0.88rem;color:#475569;padding:3px 0;">• &nbsp;{unread_rep_count} new reply from Class Rep</div>'

    if items:
        st.markdown(f"""
        <div class="activity-strip">
            <div style="font-size:0.75rem;font-weight:700;letter-spacing:1px;
                text-transform:uppercase;color:{primary};margin-bottom:8px;">🔔 Recent Activity</div>
            {items}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success("✅ Everything is up to date.")

    # ── Tabs ──────────────────────────────────────────────────
    notices_label = f"🔔 Notices ({unread_count})"   if unread_count      else "🔔 Notices"
    replies_label = f"💬 Replies ({unread_rep_count})" if unread_rep_count else "💬 Replies"

    (tab_home, tab_notices, tab_materials, tab_group,
     tab_message, tab_replies, tab_profile, tab_ai) = st.tabs([
        "🏠 Home", notices_label, "📚 Materials",
        "👥 My Group", "✉️ Message", replies_label,
        "👤 Profile", "🤖 AI Assistant"
    ])

    # ════════════════════════════════════════
    # 🏠 HOME
    # ════════════════════════════════════════
    with tab_home:
        c1,c2,c3,c4 = st.columns(4)
        with c1: metric_card("Unread",    unread_count,        "🔔", primary)
        with c2: metric_card("Materials", len(materials_list), "📚", primary)
        with c3: metric_card("Group",     s_group,             "👥", primary)
        with c4: metric_card("Year",      s_year,              "📅", primary)
        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        if urgent_unread:
            st.markdown("### 🚨 Urgent — Action Required")
            for uidx, ann in enumerate(urgent_unread):
                ann_text = ann.get("text", str(ann)) if isinstance(ann, dict) else str(ann)
                ann_id   = ann.get("id",  ann_text[:20]) if isinstance(ann, dict) else ann_text[:20]
                st.markdown(f'<div class="ann-card urgent"><span class="ann-badge badge-urgent">🚨 URGENT</span><div>{ann_text}</div></div>', unsafe_allow_html=True)
                if st.button("✅ Mark as Read", key=f"home_read_{uidx}"):
                    st.session_state.read_announcements.append(ann_id)
                    st.rerun()

        normal_unread = [a for a in unread if a not in urgent_unread]
        if normal_unread:
            st.markdown("### 📢 Latest Notice")
            ann      = normal_unread[0]
            ann_text = ann.get("text", str(ann)) if isinstance(ann, dict) else str(ann)
            st.markdown(f'<div class="ann-card"><span class="ann-badge badge-normal">NOTICE</span><div>{ann_text}</div></div>', unsafe_allow_html=True)
            if len(normal_unread) > 1:
                st.caption(f"+ {len(normal_unread)-1} more in Notices tab")

        if not urgent_unread and not normal_unread:
            st.success("✅ You're all caught up!")

    # ════════════════════════════════════════
    # 🔔 NOTICES
    # ════════════════════════════════════════
    with tab_notices:
        st.markdown("### 🔔 Noticeboard")
        if unread_count:
            st.warning(f"You have **{unread_count} unread** announcement(s)")

        if all_anns:
            for idx, ann in enumerate(all_anns):
                ann_text = ann.get("text",     str(ann)) if isinstance(ann, dict) else str(ann)
                ann_id   = ann.get("id",  ann_text[:20]) if isinstance(ann, dict) else ann_text[:20]
                priority = ann.get("priority", "normal").lower() if isinstance(ann, dict) else "normal"
                is_read  = ann_id in st.session_state.read_announcements
                is_global = isinstance(ann, dict) and ann.get("dept","") == "ALL"

                badge = "🌐 BROADCAST" if is_global else ("🚨 URGENT" if priority=="urgent" else "NOTICE")
                card_cls = "urgent" if priority=="urgent" and not is_read else ("read" if is_read else "")
                badge_cls = "badge-urgent" if priority=="urgent" else ("badge-read" if is_read else "badge-normal")

                with st.expander(f"{'✅' if is_read else '🔴' if priority=='urgent' else '🟡'} {ann_text[:60]}..."):
                    st.markdown(f'<div class="ann-card {card_cls}" style="margin:0;"><span class="ann-badge {badge_cls}">{badge}</span><div>{ann_text}</div></div>', unsafe_allow_html=True)
                    if not is_read:
                        if st.checkbox("✅ Mark as Read", key=f"notice_{idx}_{ann_id}"):
                            st.session_state.read_announcements.append(ann_id)
                            st.rerun()
                    else:
                        st.caption("✅ Read")
        else:
            st.info("No announcements yet.")

    # ════════════════════════════════════════
    # 📚 MATERIALS
    # ════════════════════════════════════════
    with tab_materials:
        st.markdown("### 📚 Course Materials")
        search   = st.text_input("🔍 Search", placeholder="Search by file name...")
        filtered = [i for i in materials_list
                    if search.lower() in (i.get("name","") if isinstance(i,dict) else str(i)).lower()]
        if filtered:
            for item in filtered:
                file_name = item.get("name","Unnamed") if isinstance(item, dict) else str(item)
                file_url  = item.get("url","#")        if isinstance(item, dict) else "#"
                ext = file_name.split(".")[-1].upper() if "." in file_name else "FILE"
                st.markdown(f'<div class="mat-row"><div class="mat-icon {"pdf" if ext=="PDF" else ""}">{ext}</div><div><strong>{file_name}</strong></div></div>', unsafe_allow_html=True)
                file_data = db.fetch_file_bytes(file_url)
                if file_data:
                    st.download_button(
                        "⬇️ Download", data=file_data,
                        file_name=file_name, mime="application/octet-stream",
                        key=f"dl_{file_name}"
                    )
                else:
                    st.warning("⚠️ File unavailable")
        else:
            st.info("No materials available for your class yet.")

    # ════════════════════════════════════════
    # 👥 MY GROUP
    # ════════════════════════════════════════
    with tab_group:
        st.markdown("### 👥 Project Group")
        if not s_group or s_group.strip() in ("", "Unassigned"):
            st.warning("⏳ You have not been assigned a group yet.")
        else:
            # Only show group members from same dept+year
            dept_col = next((c for c in ["Department","department","dept"]
                             if c in df_profiles.columns), None)
            year_col = next((c for c in ["Year","year"]
                             if c in df_profiles.columns), None)

            if dept_col and year_col:
                df_class = df_profiles[
                    (df_profiles[dept_col] == s_dept) &
                    (df_profiles[year_col] == s_year)
                ]
            else:
                df_class = df_profiles

            group_members = df_class[df_class["Assigned Group"] == s_group]

            st.markdown(f'<div class="group-banner"><div style="font-size:0.7rem;opacity:0.7;text-transform:uppercase;letter-spacing:2px;">Assigned Group</div><div style="font-size:2rem;font-weight:900;">{s_group}</div><div style="font-size:0.82rem;opacity:0.65;">{len(group_members)} member(s) · {s_dept_name} · {s_year}</div></div>', unsafe_allow_html=True)

            for _, member in group_members.iterrows():
                m_name   = member["Student Name"]
                m_reg    = member["Reg Number"]
                m_course = member.get("Course Code","")
                is_you   = (m_reg == s_reg)
                you_html = '<span style="background:#dbeafe;color:#1a56db;font-size:0.65rem;font-weight:700;padding:1px 8px;border-radius:10px;margin-left:6px;">You</span>' if is_you else ""
                av_cls   = "avatar you" if is_you else "avatar"
                st.markdown(f'<div class="member-card"><div class="{av_cls}">{m_name[0].upper()}</div><div><div style="font-weight:700;">{m_name}{you_html}</div><div style="font-size:0.75rem;color:#94a3b8;">{m_course} · {m_reg}</div></div></div>', unsafe_allow_html=True)

    # ════════════════════════════════════════
    # ✉️ MESSAGE
    # ════════════════════════════════════════
    with tab_message:
        st.markdown("### 📬 Message Class Rep")
        st.markdown(f'<div class="msg-info-card">🔒 <strong>Private & Confidential</strong> — Only your {s_year} Class Rep can see your message.</div>', unsafe_allow_html=True)

        all_feedback = db.fetch_feedback(dept=s_dept, year=s_year)
        my_messages  = [
            m for m in all_feedback
            if isinstance(m, list) and len(m) >= 5
            and str(m[1]).strip().lower() == s_reg.strip().lower()
        ]

        if my_messages:
            st.markdown("#### 📤 Sent Messages")
            _, col_b = st.columns([3,1])
            with col_b:
                if not st.session_state.confirm_clear_all:
                    if st.button("🗑️ Clear All"):
                        st.session_state.confirm_clear_all = True
                        st.rerun()

            if st.session_state.confirm_clear_all:
                st.warning("⚠️ Delete ALL your messages?")
                ca, cb = st.columns(2)
                with ca:
                    if st.button("✅ Yes, delete all"):
                        if db.delete_all_feedback(s_reg):
                            st.session_state.confirm_clear_all = False
                            st.rerun()
                with cb:
                    if st.button("❌ Cancel"):
                        st.session_state.confirm_clear_all = False
                        st.rerun()

            for midx, msg in enumerate(my_messages):
                ts     = str(msg[0])
                status = str(msg[3])
                text   = str(msg[4])
                sc     = "#16a34a" if status.lower()=="reviewed" else "#d4820a"
                st.markdown(f'<div style="background:white;border-radius:10px;padding:14px;margin-bottom:8px;border:1px solid #e2e8f7;border-left:4px solid {primary};"><div style="font-size:0.78rem;color:#94a3b8;">🕐 {ts} · <span style="color:{sc};font-weight:600;">{status}</span></div><div style="font-size:0.9rem;margin-top:4px;">{text}</div></div>', unsafe_allow_html=True)
                if st.button("🗑️ Delete", key=f"del_msg_{midx}"):
                    if db.delete_feedback(ts, s_reg):
                        st.rerun()

        st.markdown("#### ✏️ New Message")
        with st.form("student_feedback_form", clear_on_submit=True):
            user_msg  = st.text_area("Type your message:", height=140)
            submit_fb = st.form_submit_button("✉️ Send Private Message")
            if submit_fb:
                if user_msg.strip():
                    if db.submit_feedback(s_reg, s_name, user_msg, dept=s_dept, year=s_year):
                        cached_fetch_feedback.clear()
                        st.success("🚀 Message delivered!")
                        st.rerun()
                    else:
                        st.error("❌ Submission failed.")
                else:
                    st.warning("Please type a message.")

    # ════════════════════════════════════════
    # 💬 REP REPLIES
    # ════════════════════════════════════════
    with tab_replies:
        st.markdown("### 💬 Messages from Class Rep")
        if unread_rep_count:
            st.info(f"📬 You have **{unread_rep_count} unread** message(s).")
        elif my_rep_replies:
            st.success("✅ All messages read.")

        if my_rep_replies:
            for ridx, reply in enumerate(my_rep_replies):
                r_time  = reply.get("timestamp",  "N/A")
                r_rep   = reply.get("rep_name",   "Class Rep")
                r_msg   = reply.get("message",    "")
                is_read = reply.get("read_status","Unread").lower() == "read"
                left    = "#16a34a" if is_read else primary
                bg      = "#f0fdf4" if is_read else "#f8fafc"

                st.markdown(f"""
                <div style="background:{bg};border:1px solid #e2e8f7;
                    border-left:4px solid {left};border-radius:12px;
                    padding:14px 18px;margin-bottom:10px;">
                    <div style="font-size:0.75rem;color:#64748b;margin-bottom:6px;">
                        👑 <strong>{r_rep}</strong> &nbsp;·&nbsp; 🕐 {r_time}
                        {'&nbsp;<span style="background:#3b82f6;color:white;font-size:0.65rem;font-weight:700;padding:2px 8px;border-radius:10px;">NEW</span>' if not is_read else ''}
                    </div>
                    <div style="font-size:0.92rem;color:#1e293b;">{r_msg}</div>
                </div>
                """, unsafe_allow_html=True)

                if not is_read:
                    if st.button("✅ Mark as Read", key=f"rep_read_{ridx}"):
                        if db.mark_rep_reply_read(r_time, s_reg):
                            cached_fetch_rep_replies.clear()
                            st.rerun()
        else:
            st.info("No messages from your Class Rep yet.")

    # ════════════════════════════════════════
    # 👤 PROFILE
    # ════════════════════════════════════════
    with tab_profile:
        st.markdown("### 👤 Student Profile")
        initial = s_name[0].upper() if s_name else "?"
        st.markdown(f"""
        <div class="profile-card">
            <div class="profile-avatar">{initial}</div>
            <div style="font-size:1.3rem;font-weight:800;color:#1e293b;">{s_name}</div>
            <div style="font-size:0.82rem;color:#94a3b8;margin-bottom:16px;">{s_reg}</div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:0.88rem;"><span style="color:#94a3b8;">Department</span><span style="font-weight:700;">{s_dept_name}</span></div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:0.88rem;"><span style="color:#94a3b8;">Year</span><span style="font-weight:700;">{s_year}</span></div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:0.88rem;"><span style="color:#94a3b8;">Course Code</span><span style="font-weight:700;">{s_course}</span></div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:0.88rem;"><span style="color:#94a3b8;">Assigned Group</span><span style="font-weight:700;">{s_group}</span></div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;font-size:0.88rem;"><span style="color:#94a3b8;">Status</span><span style="font-weight:700;color:#16a34a;">✅ Active</span></div>
        </div>
        """, unsafe_allow_html=True)

    # ════════════════════════════════════════
    # 🤖 AI ASSISTANT
    # ════════════════════════════════════════
    with tab_ai:
        from ai_engine import extract_pdf_text

        if not st.session_state.show_ai_tab:
            st.markdown(f"""
            <div class="welcome-banner" style="text-align:center;">
                <div style="font-size:2.5rem;margin-bottom:10px;">🤖</div>
                <h2>AI Study Assistant</h2>
                <p>Ask academic questions or select a course material for AI-powered help.</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("▶ Start AI Assistant", use_container_width=True):
                st.session_state.show_ai_tab = True
                st.rerun()
        else:
            ct, cc = st.columns([4,1])
            with ct: st.markdown("### 🤖 AI Study Assistant")
            with cc:
                if st.button("✖ Close", use_container_width=True):
                    for k in ["ai_chat_history","ai_summary_shown",
                              "ai_pdf_text","ai_selected_file","show_ai_tab"]:
                        st.session_state[k] = [] if k=="ai_chat_history" else \
                                              (False if "shown" in k or "tab" in k else "")
                    st.rerun()

            st.markdown(f'<div class="msg-info-card">💡 Select a course material or ask any academic question.</div>', unsafe_allow_html=True)

            mat_names     = ["— No material (general Q&A) —"] + [m.get("name","") for m in materials_list]
            selected_name = st.selectbox("📄 Select a course material:", mat_names)

            if selected_name != "— No material (general Q&A) —":
                sel_mat = next((m for m in materials_list if m.get("name") == selected_name), None)
                if sel_mat:
                    file_url  = sel_mat.get("url","")
                    file_name = sel_mat.get("name","")
                    if st.session_state.ai_selected_file != file_name:
                        st.session_state.ai_selected_file = file_name
                        st.session_state.ai_summary_shown = False
                        st.session_state.ai_chat_history  = []
                        with st.spinner("📖 Reading material..."):
                            st.session_state.ai_pdf_text = extract_pdf_text(file_url, file_name)
                    if not st.session_state.ai_summary_shown:
                        with st.spinner("✍️ Generating summary..."):
                            summary = ai_study.summarize_material(
                                st.session_state.ai_pdf_text, file_name, student_reg=s_reg
                            )
                        st.markdown(f'<div class="ann-card"><span class="ann-badge badge-normal">📋 SUMMARY</span><div>{summary}</div></div>', unsafe_allow_html=True)
                        st.session_state.ai_summary_shown = True
                        st.session_state.ai_chat_history.append(
                            {"role":"assistant","content":f"Summary of {file_name}:\n{summary}"}
                        )
            else:
                if st.session_state.ai_selected_file:
                    st.session_state.ai_selected_file = ""
                    st.session_state.ai_pdf_text      = ""
                    st.session_state.ai_summary_shown = False
                    st.session_state.ai_chat_history  = []

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            for turn in st.session_state.ai_chat_history:
                if turn["role"] == "user":
                    st.markdown(f'<div style="background:{light};border-radius:10px;padding:10px 14px;margin-bottom:8px;margin-left:20%;text-align:right;"><div style="font-size:0.78rem;color:{primary};font-weight:600;">You</div><div style="font-size:0.9rem;">{turn["content"]}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="background:white;border:1px solid #e2e8f7;border-radius:10px;padding:10px 14px;margin-bottom:8px;margin-right:20%;"><div style="font-size:0.78rem;color:{primary};font-weight:600;">🤖 AI</div><div style="font-size:0.9rem;">{turn["content"]}</div></div>', unsafe_allow_html=True)

            with st.form("ai_chat_form", clear_on_submit=True):
                user_question = st.text_area(
                    "Your question:", height=90, label_visibility="collapsed",
                    placeholder="Ask any academic question..."
                )
                c1, c2 = st.columns([3,1])
                with c1: send_btn  = st.form_submit_button("📨 Ask AI", use_container_width=True)
                with c2: clear_btn = st.form_submit_button("🗑️ Clear",  use_container_width=True)

                if send_btn and user_question.strip():
                    with st.spinner("🤖 Thinking..."):
                        answer = ai_study.ask_ai(
                            question=user_question.strip(),
                            chat_history=st.session_state.ai_chat_history,
                            pdf_text=st.session_state.ai_pdf_text,
                            file_name=st.session_state.ai_selected_file,
                            student_reg=s_reg
                        )
                    st.session_state.ai_chat_history.append({"role":"user","content":user_question.strip()})
                    st.session_state.ai_chat_history.append({"role":"assistant","content":answer})
                    st.rerun()

                if clear_btn:
                    st.session_state.ai_chat_history  = []
                    st.session_state.ai_summary_shown = False
                    st.rerun()

    # ── Logout ────────────────────────────────────────────────
    st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
    if st.button("🔒 Log Out"):
        keys = [
            "student_logged_in","read_announcements","open_expanders",
            "show_ai_tab","ai_chat_history","ai_pdf_text",
            "ai_selected_file","ai_summary_shown",
            "confirm_clear_all","go_to_home"
        ]
        for k in keys:
            if k in st.session_state: del st.session_state[k]
        for k in [k for k in st.session_state if k.startswith("ai_last_request_")]:
            del st.session_state[k]
        st.rerun()