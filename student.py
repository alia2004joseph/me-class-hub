"""
student.py — Student Portal UI.
Read receipts removed. Dept+year scoped. Coloured themes per department.
"""
import streamlit as st
from database import SheetDatabaseManager
from cache import cached_fetch_feedback, cached_fetch_rep_replies
from config import (
    get_departments, YEARS,
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
        "ai_summary_text":    "",
        "ai_quick_q":         "",
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
    if "show_forgot_pin"  not in st.session_state: st.session_state.show_forgot_pin  = False
    if "show_set_pin"     not in st.session_state: st.session_state.show_set_pin     = False
    if "pending_reg"      not in st.session_state: st.session_state.pending_reg      = ""
    if "show_change_pin"  not in st.session_state: st.session_state.show_change_pin  = False

    if not st.session_state.student_logged_in and not st.session_state.show_reg_form:

        # ── Forgot PIN flow ──────────────────────────────────
        if st.session_state.show_forgot_pin:
            st.subheader("🔑 Reset Your PIN")
            st.info("Enter your Registration Number and the Contact Number you registered with.")

            with st.form("reset_pin_form", clear_on_submit=True):
                reset_reg     = st.text_input("Registration Number", placeholder="25/U/0000/PS").strip().upper()
                reset_contact = st.text_input("Contact Number",      placeholder="e.g. 0741234567")
                reset_pin1    = st.text_input("New PIN (4 digits)",   type="password", max_chars=6)
                reset_pin2    = st.text_input("Confirm New PIN",      type="password", max_chars=6)
                c1, c2        = st.columns(2)
                with c1: reset_btn  = st.form_submit_button("✅ Reset PIN",  use_container_width=True)
                with c2: cancel_btn = st.form_submit_button("← Back",        use_container_width=True)

                if cancel_btn:
                    st.session_state.show_forgot_pin = False
                    st.rerun()

                if reset_btn:
                    if not reset_reg or not reset_contact or not reset_pin1:
                        st.warning("Please fill in all fields.")
                    elif not reset_pin1.isdigit() or len(reset_pin1) < 4:
                        st.error("❌ PIN must be at least 4 digits.")
                    elif reset_pin1 != reset_pin2:
                        st.error("❌ PINs do not match.")
                    else:
                        with st.spinner("Verifying..."):
                            result = db.reset_pin(reset_reg, reset_contact, reset_pin1)
                        if result.get("status") == "success":
                            st.success("✅ PIN reset successfully! You can now log in.")
                            st.session_state.show_forgot_pin = False
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('message','Failed')}")

        # ── First-time PIN setup ─────────────────────────────
        elif st.session_state.show_set_pin:
            st.subheader("🔐 Set Your PIN")
            st.info(
                f"Welcome! This is your first login. "
                f"Please set a 4-digit PIN for future logins."
            )
            with st.form("set_pin_form", clear_on_submit=True):
                pin1 = st.text_input("Choose a PIN (4 digits)", type="password", max_chars=6)
                pin2 = st.text_input("Confirm PIN",              type="password", max_chars=6)
                if st.form_submit_button("✅ Set PIN & Log In", use_container_width=True):
                    if not pin1:
                        st.warning("Please enter a PIN.")
                    elif not pin1.isdigit() or len(pin1) < 4:
                        st.error("❌ PIN must be at least 4 digits (numbers only).")
                    elif pin1 != pin2:
                        st.error("❌ PINs do not match.")
                    else:
                        with st.spinner("Saving PIN..."):
                            ok = db.set_pin(st.session_state.pending_reg, pin1)
                        if ok:
                            st.session_state.student_logged_in = st.session_state.pending_reg
                            st.session_state.show_set_pin      = False
                            st.session_state.pending_reg       = ""
                            st.rerun()
                        else:
                            st.error("❌ Could not save PIN. Please try again.")

        # ── Normal login ─────────────────────────────────────
        else:
            st.subheader("🔑 Student Login")
            login_reg = st.text_input(
                "Registration Number", placeholder="e.g., 25/U/0000/PS"
            ).strip().upper()
            login_pin = st.text_input(
                "PIN", type="password", max_chars=6,
                placeholder="Enter your 4-digit PIN"
            )
            c1, c2 = st.columns(2)
            with c1: login_btn = st.button("🔓 Log In",              use_container_width=True)
            with c2: reg_btn   = st.button("📝 Register New Account", use_container_width=True)

            if st.button("🔑 Forgot PIN?", type="secondary"):
                st.session_state.show_forgot_pin = True
                st.rerun()

            if reg_btn:
                st.session_state.show_reg_form = True
                st.rerun()

            if login_btn:
                if not login_reg:
                    st.warning("Please enter your Registration Number.")
                elif not login_pin:
                    st.warning("Please enter your PIN.")
                else:
                    with st.spinner("Verifying..."):
                        result = db.verify_student(login_reg, login_pin)

                    if result.get("status") == "success":
                        if not result.get("pin_set", True):
                            # First login — no PIN set yet, go to set PIN screen
                            st.session_state.pending_reg  = login_reg
                            st.session_state.show_set_pin = True
                            st.rerun()
                        else:
                            st.session_state.student_logged_in = login_reg
                            st.rerun()
                    else:
                        msg = result.get("message", "Login failed")
                        st.error(f"❌ {msg}")
                        if "PIN" in msg or "not found" in msg:
                            st.caption("Forgot your PIN? Click 'Forgot PIN?' above to reset it.")

    # ════════════════════════════════════════════════════════
    # REGISTRATION
    # ════════════════════════════════════════════════════════
    if st.session_state.show_reg_form:
        st.subheader("📝 Create New Student Account")

        # Dept + Year + Course OUTSIDE the form so course codes update instantly
        dept_options  = {f"{v['name']} ({k})": k for k, v in get_departments().items()}
        dept_label    = st.selectbox("Department",    list(dept_options.keys()), key="reg_dept_select")
        selected_dept = dept_options[dept_label]
        year          = st.selectbox("Year of Study", YEARS,                     key="reg_year_select")
        courses       = dept_courses(selected_dept)
        code          = st.selectbox("Course Code",   courses,                   key="reg_course_select")

        with st.form("register_form", clear_on_submit=True):
            name    = st.text_input("Full Name",           placeholder="e.g., Obema Kelly")
            reg     = st.text_input("Registration Number", placeholder="25/U/0000/PS").strip().upper()
            contact = st.text_input("Contact Info",        placeholder="e.g., 074421539",
                                    help="Used to verify your identity if you forget your PIN")
            pin1    = st.text_input("Set a PIN (4 digits)", type="password", max_chars=6,
                                    placeholder="e.g. 1234",
                                    help="You will use this PIN to log in every time")
            pin2    = st.text_input("Confirm PIN",          type="password", max_chars=6)
            submit  = st.form_submit_button("✅ Register")

            if submit:
                if not name or not reg:
                    st.warning("Name and Registration Number are required.")
                elif not pin1:
                    st.warning("Please set a PIN.")
                elif not pin1.isdigit() or len(pin1) < 4:
                    st.error("❌ PIN must be at least 4 digits (numbers only).")
                elif pin1 != pin2:
                    st.error("❌ PINs do not match.")
                else:
                    ok = db.register_student(
                        name=name, reg=reg, code=code,
                        contact=contact, dept=selected_dept, year=year
                    )
                    if ok:
                        # Save PIN after successful registration
                        db.set_pin(reg, pin1)
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
     tab_message, tab_replies, tab_timetable,
     tab_profile, tab_ai) = st.tabs([
        "🏠 Home", notices_label, "📚 Materials",
        "👥 My Group", "✉️ Message", replies_label,
        "📅 Timetable", "👤 Profile", "🤖 AI Assistant"
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

        # Search + filter
        col_s, col_f = st.columns([3,1])
        with col_s:
            ann_search = st.text_input("🔍 Search notices", placeholder="Search by keyword...",
                                       key="ann_search_input")
        with col_f:
            ann_filter = st.selectbox("Filter", ["All", "Unread", "Urgent", "Broadcast"],
                                      key="ann_filter_sel")

        display_anns = all_anns
        if ann_search:
            display_anns = [a for a in display_anns
                            if ann_search.lower() in
                            (a.get("text","") if isinstance(a,dict) else str(a)).lower()]
        if ann_filter == "Unread":
            display_anns = [a for a in display_anns
                            if (a.get("id", a.get("text",""))[:20]
                                if isinstance(a,dict) else str(a)[:20])
                               not in st.session_state.read_announcements]
        elif ann_filter == "Urgent":
            display_anns = [a for a in display_anns
                            if isinstance(a,dict) and a.get("priority","").lower()=="urgent"]
        elif ann_filter == "Broadcast":
            display_anns = [a for a in display_anns
                            if isinstance(a,dict) and a.get("dept","")=="ALL"]

        st.caption(f"Showing {len(display_anns)} of {len(all_anns)} notices")

        if display_anns:
            for idx, ann in enumerate(display_anns):
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
    # 📅 TIMETABLE
    # ════════════════════════════════════════
    with tab_timetable:
        st.markdown("### 📅 Class Timetable")

        # Auto-colour helper (same logic as rep side)
        TT_PALETTE = [
            "#1a56db","#16a34a","#ea580c","#7c3aed",
            "#dc2626","#db2777","#0d9488","#b45309",
            "#0284c7","#4338ca","#e11d48","#475569"
        ]
        TT_LIGHTS = [
            "#dbeafe","#dcfce7","#ffedd5","#ede9fe",
            "#fee2e2","#fce7f3","#ccfbf1","#fef3c7",
            "#e0f2fe","#e0e7ff","#ffe4e6","#f1f5f9"
        ]
        def auto_color_s(course_name):
            idx = sum(ord(c) for c in course_name.upper()) % len(TT_PALETTE)
            return TT_PALETTE[idx], TT_LIGHTS[idx]

        timetable = db.fetch_timetable(dept=s_dept, year=s_year)

        if not timetable:
            st.info("Your Class Rep has not posted a timetable yet. Check back later.")
        else:
            day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            by_day    = {}
            for entry in timetable:
                d = entry.get("day","Other")
                by_day.setdefault(d, []).append(entry)

            # View toggle — List or Grid
            view_mode = st.radio(
                "View", ["📋 List", "🗓️ Grid"],
                horizontal=True, label_visibility="collapsed",
                key="tt_view_mode"
            )

            # Filter by type
            tt_filter = st.radio(
                "Show", ["All","Weekly","One-off"],
                horizontal=True, label_visibility="collapsed",
                key="tt_type_filter"
            )

            # Apply type filter
            if tt_filter != "All":
                for d in by_day:
                    by_day[d] = [e for e in by_day[d]
                                 if e.get("type","Weekly") == tt_filter]

            if view_mode == "📋 List":
                # ── List view ────────────────────────────────
                for day in day_order:
                    if day not in by_day or not by_day[day]:
                        continue
                    st.markdown(f"""
                    <div style="background:{primary};color:white;border-radius:10px;
                        padding:8px 16px;margin:12px 0 6px 0;font-weight:700;font-size:0.9rem;">
                        📅 {day}
                    </div>
                    """, unsafe_allow_html=True)

                    entries = sorted(by_day[day], key=lambda x: x.get("time",""))
                    for entry in entries:
                        e_color   = entry.get("color","") or auto_color_s(entry.get("course",""))[0]
                        lect      = entry.get("lecturer","")
                        is_oneoff = entry.get("type","Weekly") == "One-off"

                        # Build sub-html as plain strings — no escaped quotes
                        lect_part  = (
                            '<div style="font-size:0.82rem;color:#475569;'
                            'font-weight:600;margin-top:4px;">'
                            + "👨‍🏫 " + lect.title() + "</div>"
                        ) if lect else ""
                        badge_part = (
                            '<span style="background:#fef3c7;color:#b45309;font-size:0.65rem;'
                            'font-weight:700;padding:1px 7px;border-radius:8px;margin-left:6px;">'
                            "ONE-OFF</span>"
                        ) if is_oneoff else ""

                        html_block = (
                            '<div style="background:white;border-radius:10px;padding:12px 18px;'
                            'margin-bottom:6px;border:1px solid #e2e8f7;'
                            'border-left:4px solid ' + e_color + ';">'
                            '<div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;">'
                            '<span style="font-weight:800;color:' + e_color + ';min-width:90px;">'
                            + entry.get("time","") + "</span>"
                            '<span style="color:#1e293b;font-weight:600;">'
                            + entry.get("course","") + "</span>"
                            + badge_part +
                            "</div>"
                            + lect_part +
                            "</div>"
                        )
                        st.markdown(html_block, unsafe_allow_html=True)

            else:
                # ── Grid view ────────────────────────────────
                active_days = [d for d in day_order if d in by_day and by_day[d]]
                if not active_days:
                    st.info("No entries to display.")
                else:
                    cols = st.columns(len(active_days))
                    for ci, day in enumerate(active_days):
                        with cols[ci]:
                            st.markdown(f"""
                            <div style="background:{primary};color:white;border-radius:8px;
                                padding:6px 10px;text-align:center;font-weight:700;
                                font-size:0.78rem;margin-bottom:8px;">{day[:3].upper()}</div>
                            """, unsafe_allow_html=True)
                            entries = sorted(by_day[day], key=lambda x: x.get("time",""))
                            for entry in entries:
                                e_color = entry.get('color','')
                                if not e_color:
                                    e_color, e_light = auto_color_s(entry.get('course',''))
                                else:
                                    _, e_light = auto_color_s(entry.get('course',''))
                                lect      = entry.get("lecturer","")
                                lect_part = (
                                    '<div style="font-size:0.7rem;color:#475569;'
                                    'font-weight:600;margin-top:3px;">'
                                    + "👨‍🏫 " + lect.title()[:18] + "</div>"
                                ) if lect else ""

                                grid_block = (
                                    '<div style="background:' + e_light + ';border-radius:8px;'
                                    'padding:8px 10px;margin-bottom:6px;'
                                    'border-left:3px solid ' + e_color + ';">'
                                    '<div style="font-size:0.7rem;font-weight:800;color:' + e_color + ';">'
                                    + entry.get("time","") + "</div>"
                                    '<div style="font-size:0.75rem;font-weight:700;color:#1e293b;margin-top:2px;">'
                                    + entry.get("course","") + "</div>"
                                    + lect_part +
                                    "</div>"
                                )
                                st.markdown(grid_block, unsafe_allow_html=True)

    # ════════════════════════════════════════
    # 👤 PROFILE
    # ════════════════════════════════════════
    with tab_profile:
        st.markdown("### 👤 Student Profile")
        initial = s_name[0].upper() if s_name else "?"

        # Current contact info
        s_contact = str(student_data.get("Contact", student_data.get("contact", "")))

        st.markdown(f"""
        <div class="profile-card">
            <div class="profile-avatar">{initial}</div>
            <div style="font-size:1.3rem;font-weight:800;color:#1e293b;">{s_name}</div>
            <div style="font-size:0.82rem;color:#94a3b8;margin-bottom:16px;">{s_reg}</div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:0.88rem;"><span style="color:#94a3b8;">Department</span><span style="font-weight:700;">{s_dept_name}</span></div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:0.88rem;"><span style="color:#94a3b8;">Year</span><span style="font-weight:700;">{s_year}</span></div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:0.88rem;"><span style="color:#94a3b8;">Course Code</span><span style="font-weight:700;">{s_course}</span></div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:0.88rem;"><span style="color:#94a3b8;">Assigned Group</span><span style="font-weight:700;">{s_group}</span></div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f1f5f9;font-size:0.88rem;"><span style="color:#94a3b8;">Contact</span><span style="font-weight:700;">{s_contact if s_contact else "Not set"}</span></div>
            <div style="display:flex;justify-content:space-between;padding:10px 0;font-size:0.88rem;"><span style="color:#94a3b8;">Status</span><span style="font-weight:700;color:#16a34a;">✅ Active</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        # Change PIN
        st.markdown("#### 🔐 Change PIN")
        if not st.session_state.show_change_pin:
            if st.button("🔐 Change My PIN", use_container_width=True):
                st.session_state.show_change_pin = True
                st.rerun()
        else:
            with st.form("change_pin_form", clear_on_submit=True):
                old_pin  = st.text_input("Current PIN",     type="password", max_chars=6)
                new_pin1 = st.text_input("New PIN",         type="password", max_chars=6)
                new_pin2 = st.text_input("Confirm New PIN", type="password", max_chars=6)
                cp1, cp2 = st.columns(2)
                with cp1: save_pin   = st.form_submit_button("✅ Save", use_container_width=True)
                with cp2: cancel_pin = st.form_submit_button("❌ Cancel", use_container_width=True)

                if cancel_pin:
                    st.session_state.show_change_pin = False
                    st.rerun()
                if save_pin:
                    if not old_pin or not new_pin1:
                        st.warning("Please fill in all fields.")
                    elif not new_pin1.isdigit() or len(new_pin1) < 4:
                        st.error("❌ PIN must be at least 4 digits.")
                    elif new_pin1 != new_pin2:
                        st.error("❌ New PINs do not match.")
                    else:
                        # Verify old PIN first
                        with st.spinner("Verifying..."):
                            check = db.verify_student(s_reg, old_pin)
                        if check.get("status") != "success":
                            st.error("❌ Current PIN is incorrect.")
                        else:
                            with st.spinner("Updating..."):
                                ok = db.set_pin(s_reg, new_pin1)
                            if ok:
                                st.success("✅ PIN changed successfully!")
                                st.session_state.show_change_pin = False
                                st.rerun()
                            else:
                                st.error("❌ Could not update PIN.")

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
        st.markdown("#### ✏️ Update Contact Info")

        if "show_update_contact" not in st.session_state:
            st.session_state.show_update_contact = False

        if not st.session_state.show_update_contact:
            if st.button("✏️ Update My Contact Number", use_container_width=True):
                st.session_state.show_update_contact = True
                st.rerun()
        else:
            with st.form("update_contact_form", clear_on_submit=True):
                new_contact = st.text_input(
                    "New Contact Number",
                    placeholder="e.g. 0741234567",
                    value=s_contact
                )
                c1, c2 = st.columns(2)
                with c1: save_c = st.form_submit_button("✅ Save", use_container_width=True)
                with c2: canc_c = st.form_submit_button("❌ Cancel", use_container_width=True)

                if canc_c:
                    st.session_state.show_update_contact = False
                    st.rerun()

                if save_c:
                    if not new_contact.strip():
                        st.warning("Please enter a contact number.")
                    else:
                        with st.spinner("Updating..."):
                            ok = db.update_contact(s_reg, new_contact.strip())
                        if ok:
                            st.success("✅ Contact updated!")
                            st.session_state.show_update_contact = False
                            from cache import cached_fetch_roster
                            cached_fetch_roster.clear()
                            st.rerun()
                        else:
                            st.error("❌ Update failed. Please try again.")

    # ════════════════════════════════════════
    # 🤖 AI ASSISTANT
    # ════════════════════════════════════════
    with tab_ai:
        from ai_engine import extract_pdf_text
        from datetime import datetime

        # ── Build full student context for aware AI ───────────
        def build_student_context():
            from config import dept_name as _dept_name
            today     = datetime.now().strftime("%A, %d %B %Y")
            tomorrow  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][
                (datetime.now().weekday() + 1) % 7]

            # Announcements text
            ann_lines = ""
            for ann in all_anns[:15]:
                if isinstance(ann, dict):
                    ann_lines += f"  [{ann.get('priority','Normal')}] {ann.get('timestamp','')} — {ann.get('text','')[:200]}\n"

            # Timetable text
            tt_lines = ""
            timetable_data = db.fetch_timetable(dept=s_dept, year=s_year)
            by_day = {}
            for entry in timetable_data:
                day = entry.get("day","")
                by_day.setdefault(day, []).append(entry)
            days_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            for day in days_order:
                if day in by_day:
                    tt_lines += f"  {day}:\n"
                    for e in sorted(by_day[day], key=lambda x: x.get("time","")):
                        tt_lines += f"    - {e.get('time','')} | {e.get('course','')} | {e.get('lecturer','')} | {e.get('type','Weekly')}\n"

            # Materials text
            mat_lines = ""
            for m in materials_list[:20]:
                mat_lines += f"  - {m.get('name','')} (URL: {m.get('url','')})\n"

            # Feedback status
            fb_lines = ""
            my_feedback = db.fetch_feedback(dept=s_dept, year=s_year)
            for fb in my_feedback:
                if isinstance(fb, list) and len(fb) >= 5:
                    if str(fb[1]).strip().upper() == s_reg.upper():
                        fb_lines += f"  [{fb[3]}] {fb[0]} — {str(fb[4])[:100]}\n"

            # Rep replies
            reply_lines = ""
            for r in my_rep_replies[:10]:
                if isinstance(r, dict):
                    reply_lines += f"  [{r.get('read_status','Unread')}] {r.get('timestamp','')} — {str(r.get('message',''))[:100]}\n"

            # Group members
            group_lines = ""
            if not df_profiles.empty and "Assigned Group" in df_profiles.columns:
                group_members = df_profiles[df_profiles["Assigned Group"] == s_group]
                for _, m in group_members.iterrows():
                    marker = " (YOU)" if m.get("Reg Number","") == s_reg else ""
                    group_lines += f"  - {m.get('Student Name','')} | {m.get('Reg Number','')} | {m.get('Course Code','')}{marker}\n"

            # Rep info
            rep_info = ""
            reps = db.fetch_reps()
            
            for rep in reps:
                if isinstance(rep, dict):
                    rep_dept = str(rep.get('dept', '')).strip().upper()
                    rep_year = str(rep.get('year', '')).strip()
                    if rep_dept == s_dept.upper() and rep_year == s_year:
                        rep_name = rep.get('rep_name') or 'Unknown'
                        rep_reg  = rep.get('rep_reg') or ''
                        rep_info = f"  Name: {rep_name} | Reg: {rep_reg} | Year: {rep_year}\\n"
                        break
            return f"""=== TODAY ===
  {today}
  Tomorrow: {tomorrow}

=== STUDENT PROFILE ===
  Name: {s_name}
  Reg Number: {s_reg}
  Department: {s_dept_name} ({s_dept})
  Year: {s_year}
  Course Code: {s_course}
  Group: {s_group}

=== MY TIMETABLE ===
{tt_lines if tt_lines else "  No timetable entries yet."}

=== CLASS ANNOUNCEMENTS (Latest 15) ===
{ann_lines if ann_lines else "  No announcements yet."}

=== AVAILABLE MATERIALS ===
{mat_lines if mat_lines else "  No materials uploaded yet."}

=== MY FEEDBACK STATUS ===
{fb_lines if fb_lines else "  No feedback sent yet."}

=== REP REPLIES TO ME ===
{reply_lines if reply_lines else "  No replies yet."}

=== MY GROUP MEMBERS ({s_group}) ===
{group_lines if group_lines else "  No group members found."}

=== MY CLASS REP ===
{rep_info if rep_info else "  No Class Rep assigned yet."}
"""

        if not st.session_state.show_ai_tab:
            st.markdown(f"""
            <div class="welcome-banner" style="text-align:center;">
                <div style="font-size:2.5rem;margin-bottom:10px;">🤖</div>
                <h2>AI Study Assistant</h2>
                <p>Ask about your timetable, announcements, materials, group — or any academic question.</p>
            </div>
            """, unsafe_allow_html=True)

            # Quick prompts
            st.markdown("**💡 Try asking:**")
            quick_cols = st.columns(2)
            quick_prompts = [
                "What do I have tomorrow?",
                "What announcements did I miss?",
                "Who is in my group?",
                "Who is my class rep?",
                "Show my feedback status",
                "What materials are available?",
            ]
            for i, qp in enumerate(quick_prompts):
                with quick_cols[i % 2]:
                    if st.button(qp, key=f"qp_{i}", use_container_width=True):
                        st.session_state.show_ai_tab   = True
                        st.session_state.ai_quick_q    = qp
                        st.rerun()

            if st.button("▶ Start AI Assistant", use_container_width=True):
                st.session_state.show_ai_tab = True
                st.rerun()
        else:
            ct, cc = st.columns([4,1])
            with ct: st.markdown("### 🤖 AI Study Assistant")
            with cc:
                if st.button("✖ Close", use_container_width=True):
                    for k in ["ai_chat_history","ai_summary_shown",
                              "ai_pdf_text","ai_selected_file",
                              "ai_summary_text","show_ai_tab","ai_quick_q"]:
                        st.session_state[k] = [] if k=="ai_chat_history" else                                               (False if "shown" in k or "tab" in k else "")
                    st.rerun()

            # ── Mode selector ─────────────────────────────────
            ai_mode = st.radio(
                "Mode:", ["💬 Class Assistant", "📚 Study Material"],
                horizontal=True, key="ai_mode_select"
            )

            # ── STUDY MATERIAL MODE ───────────────────────────
            if ai_mode == "📚 Study Material":
                st.markdown(f'<div class="msg-info-card">💡 Select a course material for AI-powered help.</div>', unsafe_allow_html=True)

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
                            st.session_state.ai_summary_text  = ""
                            st.session_state.ai_chat_history  = []
                            with st.spinner("📖 Reading material..."):
                                st.session_state.ai_pdf_text = extract_pdf_text(file_url, file_name)
                        if not st.session_state.ai_summary_shown:
                            with st.spinner("✍️ Generating summary..."):
                                summary = ai_study.summarize_material(
                                    st.session_state.ai_pdf_text, file_name, student_reg=s_reg
                                )
                            st.session_state.ai_summary_text  = summary
                            st.session_state.ai_summary_shown = True

                        if st.session_state.get("ai_summary_text"):
                            st.markdown(
                                f'<div class="ann-card"><span class="ann-badge badge-normal">'
                                f'📋 SUMMARY</span><div>{st.session_state.ai_summary_text}</div></div>',
                                unsafe_allow_html=True
                            )

                        # Revision questions button
                        if st.button("🎯 Generate Revision Questions", use_container_width=True):
                            with st.spinner("Generating questions..."):
                                qs = ai_study.generate_revision_questions(
                                    topic=file_name,
                                    pdf_text=st.session_state.ai_pdf_text,
                                    file_name=file_name,
                                    student_reg=s_reg
                                )
                            st.markdown(qs)
                else:
                    if st.session_state.ai_selected_file:
                        st.session_state.ai_selected_file = ""
                        st.session_state.ai_pdf_text      = ""
                        st.session_state.ai_summary_shown = False
                        st.session_state.ai_summary_text  = ""
                        st.session_state.ai_chat_history  = []

            # ── CLASS ASSISTANT MODE ──────────────────────────
            else:
                st.markdown(f'<div class="msg-info-card">💡 Ask about your timetable, announcements, materials, group, rep, or any academic topic.</div>', unsafe_allow_html=True)

            st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

            # ── Chat history display ──────────────────────────
            for turn in st.session_state.ai_chat_history:
                if turn["role"] == "user":
                    st.markdown(f'<div style="background:{light};border-radius:10px;padding:10px 14px;margin-bottom:8px;margin-left:20%;text-align:right;"><div style="font-size:0.78rem;color:{primary};font-weight:600;">You</div><div style="font-size:0.9rem;">{turn["content"]}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="background:white;border:1px solid #e2e8f7;border-radius:10px;padding:10px 14px;margin-bottom:8px;margin-right:20%;"><div style="font-size:0.78rem;color:{primary};font-weight:600;">🤖 AI</div><div style="font-size:0.9rem;">{turn["content"]}</div></div>', unsafe_allow_html=True)

            # ── Handle quick prompt ───────────────────────────
            if st.session_state.get("ai_quick_q"):
                quick_q = st.session_state.ai_quick_q
                st.session_state.ai_quick_q = ""
                with st.spinner("🤖 Thinking..."):
                    ctx    = build_student_context()
                    answer = ai_study.chat_with_context(
                        question       = quick_q,
                        chat_history   = st.session_state.ai_chat_history,
                        student_context= ctx,
                        pdf_text       = st.session_state.ai_pdf_text,
                        file_name      = st.session_state.ai_selected_file,
                        student_reg    = s_reg
                    )
                st.session_state.ai_chat_history.append({"role":"user",      "content": quick_q})
                st.session_state.ai_chat_history.append({"role":"assistant", "content": answer})
                st.rerun()

            # ── Chat input ────────────────────────────────────
            with st.form("ai_chat_form", clear_on_submit=True):
                placeholder = (
                    "Ask about your timetable, announcements, group, rep, materials..."
                    if ai_mode == "💬 Class Assistant"
                    else "Ask any academic question about the selected material..."
                )
                user_question = st.text_area(
                    "Your question:", height=90, label_visibility="collapsed",
                    placeholder=placeholder
                )
                c1, c2 = st.columns([3,1])
                with c1: send_btn  = st.form_submit_button("📨 Ask AI", use_container_width=True)
                with c2: clear_btn = st.form_submit_button("🗑️ Clear",  use_container_width=True)

                if send_btn and user_question.strip():
                    with st.spinner("🤖 Thinking..."):
                        if ai_mode == "💬 Class Assistant":
                            ctx    = build_student_context()
                            answer = ai_study.chat_with_context(
                                question        = user_question.strip(),
                                chat_history    = st.session_state.ai_chat_history,
                                student_context = ctx,
                                pdf_text        = st.session_state.ai_pdf_text,
                                file_name       = st.session_state.ai_selected_file,
                                student_reg     = s_reg
                            )
                        else:
                            answer = ai_study.ask_ai(
                                question     = user_question.strip(),
                                chat_history = st.session_state.ai_chat_history,
                                pdf_text     = st.session_state.ai_pdf_text,
                                file_name    = st.session_state.ai_selected_file,
                                student_reg  = s_reg
                            )
                    st.session_state.ai_chat_history.append({"role":"user",      "content": user_question.strip()})
                    st.session_state.ai_chat_history.append({"role":"assistant", "content": answer})
                    st.rerun()

                if clear_btn:
                    st.session_state.ai_chat_history  = []
                    st.session_state.ai_summary_shown = False
                    st.session_state.ai_summary_text  = ""
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