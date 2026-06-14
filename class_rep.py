"""
class_rep.py — Class Representative Dashboard.
Login now verified against Reps Sheet via GAS (no secrets.toml needed).
Rep sees only their dept+year data. Includes Change Password feature.
"""
import streamlit as st
from database import SheetDatabaseManager
from ai_engine import AISortingEngine, AIRepAssistant
from config import get_departments, YEARS, dept_color, dept_light, dept_name, dept_courses


def inject_rep_css(primary: str, light: str):
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    html,body,[class*="css"]{{font-family:'Plus Jakarta Sans',sans-serif;}}
    #MainMenu,footer{{visibility:hidden;}}
    .stApp{{background:#F0F4FF;}}
    .rep-banner{{
        background:linear-gradient(135deg,{primary} 0%,{primary}cc 100%);
        border-radius:18px;padding:28px 32px;margin-bottom:24px;color:white;
    }}
    .rep-banner h2{{font-size:1.6rem;font-weight:800;margin:0 0 6px 0;color:white;}}
    .rep-badge{{
        display:inline-block;background:rgba(255,255,255,0.15);
        border:1px solid rgba(255,255,255,0.25);border-radius:20px;
        padding:4px 14px;font-size:0.75rem;font-weight:600;color:white;margin-right:6px;
    }}
    .fb-card{{
        background:white;border-radius:12px;padding:16px 18px;margin-bottom:10px;
        border:1px solid #e2e8f7;border-left:4px solid {primary};
    }}
    .fb-card.reviewed{{border-left-color:#16a34a;opacity:0.85;}}
    .pro-divider{{height:1px;background:#e2e8f7;margin:22px 0;}}
    .scope-badge{{
        background:{light};color:{primary};border:1px solid {primary}44;
        border-radius:8px;padding:8px 16px;font-weight:700;font-size:0.85rem;
        display:inline-block;margin-bottom:16px;
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


def render_class_rep_interface(
    db: SheetDatabaseManager,
    ai: AISortingEngine,
    ai_rep: AIRepAssistant,
):
    # ── Session init ─────────────────────────────────────────
    defaults = {
        "rep_logged_in":       False,
        "rep_dept":            None,
        "rep_year":            None,
        "rep_name":            "",
        "rep_reg":             "",
        "rep_ai_draft":        "",
        "rep_ai_reply":        "",
        "rep_confirm_delete":  None,
        "rep_show_change_pw":  False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    st.title("👑 Class Rep Dashboard")
    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # LOGIN — verified against Reps Sheet via GAS
    # ════════════════════════════════════════════════════════
    if not st.session_state.rep_logged_in:
        st.subheader("🔐 Class Rep Login")
        st.info("Your login is managed by your department admin. Contact them if you cannot log in.")

        dept_options  = {f"{v['name']} ({k})": k for k, v in get_departments().items()}
        dept_label    = st.selectbox("Your Department", list(dept_options.keys()), key="rep_login_dept")
        selected_dept = dept_options[dept_label]
        selected_year = st.selectbox("Your Year Group", YEARS, key="rep_login_year")
        password_input = st.text_input("Password", type="password", key="rep_login_pw")

        if st.button("🔓 Log In", use_container_width=True):
            if not password_input:
                st.warning("Please enter your password.")
            else:
                with st.spinner("Verifying..."):
                    result = db.verify_rep(selected_dept, selected_year, password_input)

                if result.get("status") == "success":
                    st.session_state.rep_logged_in = True
                    st.session_state.rep_dept      = selected_dept
                    st.session_state.rep_year      = selected_year
                    st.session_state.rep_name      = result.get("rep_name", "Class Rep")
                    st.session_state.rep_reg       = result.get("rep_reg",  "")
                    st.rerun()
                else:
                    msg = result.get("message", "Invalid credentials")
                    if "No reps configured" in msg:
                        st.error("❌ No rep account exists for this dept/year yet. Ask your Super Admin to create one.")
                    else:
                        st.error(f"❌ {msg}")
        return

    # ── Logged in ────────────────────────────────────────────
    r_dept  = st.session_state.rep_dept
    r_year  = st.session_state.rep_year
    r_name  = st.session_state.rep_name
    r_reg   = st.session_state.rep_reg
    primary = dept_color(r_dept)
    light   = dept_light(r_dept)
    d_name  = dept_name(r_dept)

    inject_rep_css(primary, light)

    st.markdown(f'<div class="scope-badge">🏛️ {d_name} &nbsp;·&nbsp; 📅 {r_year} &nbsp;·&nbsp; 👑 {r_name}</div>', unsafe_allow_html=True)

    # ── Fetch scoped data ────────────────────────────────────
    df_class      = db.fetch_roster(dept=r_dept, year=r_year)
    announcements = db.fetch_announcements(dept=r_dept, year=r_year)
    materials     = db.fetch_materials(dept=r_dept, year=r_year)
    feedback_list = db.fetch_feedback(dept=r_dept, year=r_year)
    rep_replies   = db.fetch_rep_replies(dept=r_dept, year=r_year)

    total_students   = len(df_class) if not df_class.empty else 0
    pending_feedback = sum(1 for f in feedback_list
                           if isinstance(f, list) and len(f) >= 4
                           and str(f[3]).lower() == "pending")
    unread_replies   = sum(1 for r in rep_replies
                           if r.get("read_status", "Unread").lower() == "unread")

    # ── Banner ───────────────────────────────────────────────
    st.markdown(f"""
    <div class="rep-banner">
        <h2>👑 {r_name}'s Dashboard</h2>
        <p style="opacity:0.75;margin:0 0 12px 0;">{d_name} — {r_year}</p>
        <span class="rep-badge">👥 {total_students} Students</span>
        <span class="rep-badge">📬 {pending_feedback} Pending</span>
        <span class="rep-badge">💬 {unread_replies} Unread Replies</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ─────────────────────────────────────────────────
    tabs = st.tabs([
        "👥 Roster", "🏷️ Groups", "📢 Notices",
        "📚 Materials", "📅 Timetable", "📬 Feedback",
        "💬 Replies", "🤖 AI Tools", "⚙️ Settings"
    ])

    # ════════════════════════════════════════
    # 👥 ROSTER
    # ════════════════════════════════════════
    with tabs[0]:
        st.markdown(f"### 👥 {d_name} — {r_year} Students")
        if df_class.empty:
            st.info("No students registered for your class yet.")
        else:
            search  = st.text_input("🔍 Search", placeholder="Name or reg number...")
            df_show = df_class.copy()
            if search:
                mask = (
                    df_show["Student Name"].str.contains(search, case=False, na=False) |
                    df_show["Reg Number"].str.contains(search, case=False, na=False)
                )
                df_show = df_show[mask]
            st.dataframe(df_show, use_container_width=True)
            st.caption(f"Showing {len(df_show)} of {total_students} students")

            # Export to CSV
            csv = df_show.to_csv(index=False)
            st.download_button(
                "⬇️ Export Class List to CSV",
                data=csv,
                file_name=f"{r_dept}_{r_year.replace(' ','_')}_students.csv",
                mime="text/csv",
                use_container_width=True
            )

            st.markdown("#### 🗑️ Delete Student")
            del_name = st.selectbox(
                "Select student",
                ["— Select —"] + list(df_class["Student Name"].values),
                key="del_student_sel"
            )
            if del_name != "— Select —":
                if st.button(f"🗑️ Delete {del_name}", type="secondary"):
                    result = db.delete_student(del_name)
                    if result.get("status") == "success":
                        st.success(f"✅ {del_name} deleted.")
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('message', 'Error')}")

            st.markdown("---")
            st.markdown("#### 🔐 Reset Student PIN")
            st.caption("Use this if a student is locked out and cannot reset their PIN themselves.")
            reset_sel = st.selectbox(
                "Select student to reset PIN",
                ["— Select —"] + list(df_class["Student Name"].values),
                key="reset_pin_sel"
            )
            if reset_sel != "— Select —":
                new_pin_rep = st.text_input(
                    "New PIN for student", type="password",
                    max_chars=6, key="rep_reset_pin_input",
                    placeholder="4-digit PIN"
                )
                if st.button("🔐 Reset PIN", key="rep_reset_pin_btn"):
                    if not new_pin_rep or not new_pin_rep.isdigit() or len(new_pin_rep) < 4:
                        st.error("❌ PIN must be at least 4 digits.")
                    else:
                        reg_row = df_class[df_class["Student Name"] == reset_sel]
                        if not reg_row.empty:
                            reg = reg_row.iloc[0]["Reg Number"]
                            with st.spinner("Resetting..."):
                                ok = db.set_pin(reg, new_pin_rep)
                            if ok:
                                st.success(f"✅ PIN reset for {reset_sel}. Share the new PIN with them securely.")
                            else:
                                st.error("❌ Reset failed.")

    # ════════════════════════════════════════
    # 🏷️ GROUPS
    # ════════════════════════════════════════
    with tabs[1]:
        st.markdown("### 🏷️ Group Allocation")
        if df_class.empty:
            st.warning("No students to allocate.")
        else:
            st.markdown("#### 🤖 AI Auto-Allocation")
            team_size    = st.slider("Students per group", 2, 10, 4)
            instructions = st.text_area(
                "Custom instructions (optional)",
                placeholder="e.g., Mix course codes, keep students with same contact apart..."
            )
            if st.button("🤖 Auto-Allocate with AI", use_container_width=True):
                with st.spinner("Generating groups..."):
                    result = ai.generate_teams(df_class, team_size, instructions)
                if "error" in result:
                    st.error(f"❌ {result['error']}")
                else:
                    st.session_state["pending_allocations"] = result
                    st.success(f"✅ {len(set(result.values()))} groups for {len(result)} students.")

            if "pending_allocations" in st.session_state:
                alloc   = st.session_state["pending_allocations"]
                preview = {}
                for reg, grp in alloc.items():
                    preview.setdefault(grp, []).append(reg)
                st.markdown("**Preview:**")
                for grp, members in preview.items():
                    st.markdown(f"**{grp}** — {', '.join(members)}")
                if st.button("✅ Save Groups", use_container_width=True, type="primary"):
                    with st.spinner("Saving..."):
                        res = db.save_group_allocations(alloc)
                    if res.get("status") == "success":
                        del st.session_state["pending_allocations"]
                        st.success("✅ Groups saved!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to save.")

            st.markdown("---")
            st.markdown("#### ✏️ Manual Assignment")
            with st.form("manual_group_form"):
                student_sel = st.selectbox("Student", df_class["Student Name"].values)
                group_name  = st.text_input("Group Name", placeholder="e.g., Team Alpha")
                if st.form_submit_button("Assign"):
                    reg = df_class[df_class["Student Name"] == student_sel]["Reg Number"].values
                    if len(reg):
                        res = db.save_group_allocations({reg[0]: group_name})
                        if res.get("status") == "success":
                            st.success(f"✅ {student_sel} → {group_name}")
                            st.rerun()

    # ════════════════════════════════════════
    # 📢 NOTICES
    # ════════════════════════════════════════
    with tabs[2]:
        st.markdown("### 📢 Announcements")
        st.info(f"Visible only to **{d_name} — {r_year}** students.")

        with st.form("post_ann_form", clear_on_submit=True):
            ann_text  = st.text_area("Announcement text", height=120)
            priority  = st.selectbox("Priority", ["Normal", "Urgent"])
            c1, c2    = st.columns(2)
            with c1: post_btn  = st.form_submit_button("📢 Post",          use_container_width=True)
            with c2: draft_btn = st.form_submit_button("✍️ Draft with AI", use_container_width=True)

            if draft_btn and ann_text.strip():
                with st.spinner("Drafting..."):
                    st.session_state.rep_ai_draft = ai_rep.draft_announcement(ann_text, priority)
            if post_btn:
                if ann_text.strip():
                    if db.post_announcement(ann_text, priority, dept=r_dept, year=r_year):
                        st.success("✅ Posted!")
                        st.rerun()
                    else:
                        st.error("❌ Failed.")
                else:
                    st.warning("Please enter text.")

        if st.session_state.rep_ai_draft:
            st.markdown("**AI Draft — edit before posting:**")
            edited = st.text_area("", value=st.session_state.rep_ai_draft, height=150, key="draft_edit")
            pri2   = st.selectbox("Priority", ["Normal", "Urgent"], key="draft_pri")
            if st.button("📢 Post this Draft"):
                if db.post_announcement(edited, pri2, dept=r_dept, year=r_year):
                    st.session_state.rep_ai_draft = ""
                    st.success("✅ Draft posted!")
                    st.rerun()

        st.markdown("---")
        st.markdown("#### 📋 Posted Announcements")
        if announcements:
            for aidx, ann in enumerate(announcements):
                ann_text_val = ann.get("text",     "") if isinstance(ann, dict) else str(ann)
                priority_val = ann.get("priority", "Normal") if isinstance(ann, dict) else "Normal"
                ts_val       = ann.get("timestamp","") if isinstance(ann, dict) else ""
                is_urgent    = priority_val.lower() == "urgent"
                left_col     = "#ef4444" if is_urgent else primary

                st.markdown(f"""
                <div style="background:white;border-radius:12px;padding:14px 18px;
                    margin-bottom:8px;border:1px solid #e2e8f7;border-left:4px solid {left_col};">
                    <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:4px;">🕐 {ts_val}</div>
                    <span style="background:{'#fee2e2' if is_urgent else light};
                        color:{left_col};font-size:0.68rem;font-weight:700;
                        padding:2px 8px;border-radius:10px;margin-right:8px;">
                        {priority_val.upper()}
                    </span>
                    <span style="font-size:0.9rem;">{ann_text_val}</span>
                </div>
                """, unsafe_allow_html=True)
                if st.button("🗑️ Delete", key=f"del_ann_{aidx}"):
                    if db.delete_announcement(ann_text_val):
                        st.rerun()
        else:
            st.info("No announcements posted yet.")

    # ════════════════════════════════════════
    # 📚 MATERIALS
    # ════════════════════════════════════════
    with tabs[3]:
        st.markdown("### 📚 Course Materials")
        st.info(f"Visible only to **{d_name} — {r_year}** students.")

        uploaded = st.file_uploader(
            "Upload a file", type=["pdf", "docx", "pptx", "xlsx", "txt"]
        )
        if uploaded and st.button("⬆️ Upload", use_container_width=True):
            with st.spinner("Uploading to Google Drive..."):
                ok = db.upload_material(
                    uploaded.read(), uploaded.name, uploaded.type,
                    dept=r_dept, year=r_year
                )
            st.success(f"✅ '{uploaded.name}' uploaded!") if ok else st.error("❌ Upload failed.")
            if ok: st.rerun()

        st.markdown("---")
        if materials:
            for midx, mat in enumerate(materials):
                m_name = mat.get("name", "Unnamed") if isinstance(mat, dict) else str(mat)
                ext    = m_name.split(".")[-1].upper() if "." in m_name else "FILE"
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:12px 16px;
                        border:1px solid #e2e8f7;">
                        <span style="background:{light};color:{primary};font-size:0.7rem;
                            font-weight:800;padding:3px 8px;border-radius:6px;margin-right:10px;">
                            {ext}
                        </span>{m_name}
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    if st.button("🗑️", key=f"del_mat_{midx}"):
                        if db.delete_material(m_name):
                            st.rerun()
        else:
            st.info("No materials uploaded yet.")


    # ════════════════════════════════════════
    # 📅 TIMETABLE
    # ════════════════════════════════════════
    with tabs[4]:
        st.markdown("### 📅 Class Timetable")
        st.info(f"Timetable for **{d_name} — {r_year}**. Students see this in their portal.")

        # Auto-colour palette — assigned by course name hash
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

        def auto_color(course_name):
            """Deterministically assign a colour based on course name."""
            idx = sum(ord(c) for c in course_name.upper()) % len(TT_PALETTE)
            return TT_PALETTE[idx], TT_LIGHTS[idx]

        timetable = db.fetch_timetable(dept=r_dept, year=r_year)

        # ── Add entry manually ───────────────────────────────
        st.markdown("#### ➕ Add Entry")
        with st.form("add_tt_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                tt_day      = st.selectbox("Day", ["Monday","Tuesday","Wednesday",
                                                    "Thursday","Friday","Saturday","Sunday"])
                tt_time     = st.text_input("Time", placeholder="e.g. 8:00 AM")
            with c2:
                tt_course   = st.text_input("Course Code / Name", placeholder="e.g. BMEC 2101")
                tt_lecturer = st.text_input("Lecturer Name",       placeholder="e.g. Dr. Okello")

            tt_type = st.radio("Session Type", ["Weekly","One-off"], horizontal=True,
                               help="Weekly = every week | One-off = single special session")

            if st.form_submit_button("➕ Add Entry", use_container_width=True):
                if not tt_time or not tt_course:
                    st.warning("Please fill in Day, Time and Course at minimum.")
                else:
                    # Auto-assign colour based on course name
                    c_hex, c_light = auto_color(tt_course)
                    with st.spinner("Saving..."):
                        ok = db.add_timetable_entry(
                            r_dept, r_year, tt_day,
                            tt_time, tt_course, tt_lecturer,
                            color=c_hex, entry_type=tt_type
                        )
                    if ok:
                        st.success(f"✅ Added: {tt_day} {tt_time} — {tt_course}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add entry.")

        st.markdown("---")

        # ── AI parse from raw text ───────────────────────────
        st.markdown("#### 🤖 Import from Raw Text")
        with st.expander("Paste raw timetable text and let AI parse it"):
            raw_tt = st.text_area("Paste timetable here:", height=150,
                placeholder="e.g. Monday 8am BMEC, Tuesday 10am BBPE...")
            if st.button("🤖 Parse & Import with AI", key="parse_tt_btn"):
                if not raw_tt.strip():
                    st.warning("Please paste some timetable text.")
                else:
                    with st.spinner("Parsing..."):
                        import json as _json
                        from ai_engine import _call_with_retry
                        from google.genai import types as _types
                        prompt = (
                            "Parse this timetable text into a JSON array. "
                            "Each item must have: day, time, course, lecturer, type. "
                            "Days must be full names (Monday, Tuesday etc). "
                            "type must be Weekly or One-off. "
                            "lecturer can be empty string if not mentioned. "
                            "Return ONLY raw JSON array, no markdown.\n\n"
                            "Timetable: " + raw_tt
                        )
                        config = _types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                        result = _call_with_retry("models/gemini-2.5-flash", prompt, config)
                        try:
                            entries = _json.loads(result)
                            added = 0
                            for entry in entries:
                                day    = entry.get("day","").strip()
                                time   = entry.get("time","").strip()
                                course = entry.get("course","").strip()
                                if day and time and course:
                                    lecturer   = entry.get("lecturer","").strip()
                                entry_type = entry.get("type","Weekly").strip()
                                c_hex, _   = auto_color(course)
                                if db.add_timetable_entry(
                                    r_dept, r_year, day, time,
                                    course, lecturer, c_hex, entry_type
                                ):
                                        added += 1
                            st.success(f"✅ Imported {added} entries!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Could not parse: {e}")

        st.markdown("---")

        # ── View & delete entries ────────────────────────────
        st.markdown("#### 📋 Current Timetable")

        if not timetable:
            st.info("No timetable entries yet.")
        else:
            # Group by day
            day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
            by_day    = {}
            for entry in timetable:
                d = entry.get("day","Other")
                by_day.setdefault(d, []).append(entry)

            for day in day_order:
                if day not in by_day:
                    continue
                st.markdown(f"**{day}**")
                entries = sorted(by_day[day], key=lambda x: x.get("time",""))
                for eidx, entry in enumerate(entries):
                    c1, c2 = st.columns([5,1])
                    with c1:
                        e_color    = entry.get('color','') or primary
                        e_lcolor,_ = auto_color(entry.get('course',''))
                        e_color    = e_color if e_color else e_lcolor
                        lect_str   = (
                            '<span style="color:#475569;font-size:0.82rem;font-weight:600;">'
                            + "👨‍🏫 " + entry.get("lecturer","").title() + "</span>"
                        ) if entry.get("lecturer") else ""
                        type_badge = f"<span style=\"background:#f1f5f9;color:#64748b;font-size:0.65rem;font-weight:700;padding:1px 7px;border-radius:8px;margin-left:6px;\">{entry.get('type','Weekly')}</span>"
                        st.markdown(f"""
                        <div style="background:white;border-radius:10px;padding:10px 16px;
                            margin-bottom:6px;border:1px solid #e2e8f7;
                            border-left:4px solid {e_color};">
                            <div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;">
                                <span style="font-weight:800;color:{e_color};min-width:90px;">{entry.get('time','')}</span>
                                <span style="color:#1e293b;font-weight:600;">{entry.get('course','')}</span>
                                {type_badge}
                            </div>
                            <div style="margin-top:3px;">{lect_str}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        if st.button("🗑️", key=f"del_tt_{day}_{eidx}"):
                            with st.spinner("Deleting..."):
                                ok = db.delete_timetable_entry(
                                    r_dept, r_year, day, entry.get("time","")
                                )
                            if ok: st.rerun()

            st.markdown("---")
            if st.button("🗑️ Clear Entire Timetable", type="secondary"):
                st.session_state["confirm_clear_tt"] = True
                st.rerun()

            if st.session_state.get("confirm_clear_tt"):
                st.warning("⚠️ Delete ALL timetable entries for this class?")
                ca, cb = st.columns(2)
                with ca:
                    if st.button("✅ Yes, clear all", key="yes_clear_tt"):
                        with st.spinner("Clearing..."):
                            db.clear_timetable(r_dept, r_year)
                        st.session_state["confirm_clear_tt"] = False
                        st.rerun()
                with cb:
                    if st.button("❌ Cancel", key="no_clear_tt"):
                        st.session_state["confirm_clear_tt"] = False
                        st.rerun()

    # ════════════════════════════════════════
    # 📬 FEEDBACK
    # ════════════════════════════════════════
    with tabs[5]:
        st.markdown("### 📬 Student Feedback Inbox")
        if not feedback_list:
            st.info("No feedback messages yet.")
        else:
            pending  = [f for f in feedback_list
                        if isinstance(f, list) and len(f) >= 4
                        and str(f[3]).lower() == "pending"]
            reviewed = [f for f in feedback_list if f not in pending]
            st.caption(f"{len(pending)} pending · {len(reviewed)} reviewed")

            if st.button("📊 Summarize All with AI"):
                with st.spinner("Analysing..."):
                    summary = ai_rep.summarize_feedback(feedback_list)
                st.markdown(summary)
                st.markdown("---")

            for fidx, fb in enumerate(feedback_list):
                if not (isinstance(fb, list) and len(fb) >= 5):
                    continue
                ts, reg, name, status, msg = (
                    str(fb[0]), str(fb[1]), str(fb[2]), str(fb[3]), str(fb[4])
                )
                is_rev   = status.lower() == "reviewed"
                sc       = "#16a34a" if is_rev else "#d4820a"
                card_cls = "fb-card reviewed" if is_rev else "fb-card"

                st.markdown(f"""
                <div class="{card_cls}">
                    <div style="font-size:0.78rem;color:#94a3b8;">
                        👤 <strong>{name}</strong> · {reg} · 🕐 {ts}
                        &nbsp;<span style="color:{sc};font-weight:600;">{status}</span>
                    </div>
                    <div style="margin-top:6px;font-size:0.9rem;">{msg}</div>
                </div>
                """, unsafe_allow_html=True)

                c1, c2, c3 = st.columns(3)
                with c1:
                    if not is_rev and st.button("✅ Mark Reviewed", key=f"rev_{fidx}"):
                        if db.update_feedback_status(ts, reg):
                            st.rerun()
                with c2:
                    if st.button("✍️ AI Suggest Reply", key=f"ai_rep_{fidx}"):
                        with st.spinner("Drafting..."):
                            st.session_state.rep_ai_reply = ai_rep.suggest_reply(name, msg)
                            st.session_state[f"reply_target_{fidx}"] = {
                                "reg": reg, "name": name, "ts": ts
                            }
                with c3:
                    if st.button("🗑️ Delete", key=f"del_fb_{fidx}"):
                        if db.delete_feedback(ts, reg):
                            st.rerun()

                if st.session_state.get(f"reply_target_{fidx}"):
                    reply_text = st.text_area(
                        "Reply:", value=st.session_state.rep_ai_reply,
                        key=f"reply_ta_{fidx}", height=100
                    )
                    if st.button("📨 Send Reply", key=f"send_rep_{fidx}"):
                        target = st.session_state[f"reply_target_{fidx}"]
                        ok = db.post_rep_reply(
                            reg_number=target["reg"], student_name=target["name"],
                            message=reply_text, rep_name=r_name,
                            dept=r_dept, year=r_year
                        )
                        if ok:
                            db.update_feedback_status(target["ts"], target["reg"])
                            st.session_state[f"reply_target_{fidx}"] = None
                            st.session_state.rep_ai_reply = ""
                            st.success("✅ Reply sent!")
                            st.rerun()

    # ════════════════════════════════════════
    # 💬 REPLIES
    # ════════════════════════════════════════
    with tabs[6]:
        st.markdown("### 💬 Sent Replies Overview")
        if not rep_replies:
            st.info("No replies sent yet.")
        else:
            for reply in rep_replies:
                r_time    = reply.get("timestamp",    "")
                r_student = reply.get("student_name", "")
                r_msg     = reply.get("message",      "")
                r_status  = reply.get("read_status",  "Unread")
                is_read   = r_status.lower() == "read"
                sc        = "#16a34a" if is_read else primary

                st.markdown(f"""
                <div style="background:white;border-radius:12px;padding:14px 18px;
                    margin-bottom:8px;border:1px solid #e2e8f7;border-left:4px solid {sc};">
                    <div style="font-size:0.75rem;color:#94a3b8;">
                        To: <strong>{r_student}</strong> · {r_time}
                        &nbsp;<span style="color:{sc};font-weight:600;">
                            {'✅ Read' if is_read else '🔵 Unread'}
                        </span>
                    </div>
                    <div style="margin-top:6px;font-size:0.9rem;">{r_msg}</div>
                </div>
                """, unsafe_allow_html=True)

    # ════════════════════════════════════════
    # 🤖 AI TOOLS
    # ════════════════════════════════════════
    with tabs[7]:
        st.markdown("### 🤖 AI Rep Tools")
        tool = st.radio("Select tool:", [
            "📅 Format Timetable",
            "🔍 Check Conflicts",
            "❓ Timetable Q&A"
        ], horizontal=True)

        if tool == "📅 Format Timetable":
            raw = st.text_area("Paste raw timetable:", height=200)
            if st.button("📅 Format with AI") and raw.strip():
                with st.spinner("Formatting..."):
                    result = ai_rep.format_timetable(raw)
                st.markdown(result)
                if st.button("📢 Post as Announcement"):
                    if db.post_announcement(result, "Normal", dept=r_dept, year=r_year):
                        st.success("✅ Posted!")

        elif tool == "🔍 Check Conflicts":
            raw = st.text_area("Paste timetable to check:", height=200)
            if st.button("🔍 Check") and raw.strip():
                with st.spinner("Checking..."):
                    result = ai_rep.check_timetable_conflicts(raw)
                st.markdown(result)

        elif tool == "❓ Timetable Q&A":
            timetable = st.text_area("Paste timetable:", height=150)
            question  = st.text_input("Question:", placeholder="When is the Engineering Maths lecture?")
            if st.button("Ask") and question.strip() and timetable.strip():
                with st.spinner("Answering..."):
                    result = ai_rep.answer_timetable_question(question, timetable)
                st.info(result)

    # ════════════════════════════════════════
    # ⚙️ SETTINGS
    # ════════════════════════════════════════
    with tabs[8]:
        st.markdown("### ⚙️ Account Settings")
        st.markdown(f"""
        <div style="background:white;border-radius:14px;padding:20px 24px;
            border:1px solid #e2e8f7;margin-bottom:20px;">
            <div style="font-size:1rem;font-weight:800;color:#1e293b;margin-bottom:12px;">
                👑 Rep Profile
            </div>
            <div style="display:flex;justify-content:space-between;padding:8px 0;
                border-bottom:1px solid #f1f5f9;font-size:0.9rem;">
                <span style="color:#94a3b8;">Name</span>
                <span style="font-weight:700;">{r_name}</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:8px 0;
                border-bottom:1px solid #f1f5f9;font-size:0.9rem;">
                <span style="color:#94a3b8;">Reg Number</span>
                <span style="font-weight:700;">{r_reg}</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:8px 0;
                border-bottom:1px solid #f1f5f9;font-size:0.9rem;">
                <span style="color:#94a3b8;">Department</span>
                <span style="font-weight:700;">{d_name}</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:8px 0;font-size:0.9rem;">
                <span style="color:#94a3b8;">Year</span>
                <span style="font-weight:700;">{r_year}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 🔑 Change Password")
        if not st.session_state.rep_show_change_pw:
            if st.button("🔑 Change My Password"):
                st.session_state.rep_show_change_pw = True
                st.rerun()
        else:
            with st.form("change_pw_form", clear_on_submit=True):
                old_pw  = st.text_input("Current Password",  type="password")
                new_pw  = st.text_input("New Password",      type="password")
                new_pw2 = st.text_input("Confirm New Password", type="password")
                c1, c2  = st.columns(2)
                with c1: save_btn   = st.form_submit_button("✅ Save", use_container_width=True)
                with c2: cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)

                if cancel_btn:
                    st.session_state.rep_show_change_pw = False
                    st.rerun()

                if save_btn:
                    if not old_pw or not new_pw:
                        st.warning("Please fill in all fields.")
                    elif new_pw != new_pw2:
                        st.error("❌ New passwords do not match.")
                    elif len(new_pw) < 6:
                        st.error("❌ New password must be at least 6 characters.")
                    else:
                        with st.spinner("Updating..."):
                            result = db.change_rep_password(r_dept, r_year, old_pw, new_pw)
                        if result.get("status") == "success":
                            st.success("✅ Password changed successfully!")
                            st.session_state.rep_show_change_pw = False
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('message', 'Failed')}")

    # ── Logout ───────────────────────────────────────────────
    st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
    if st.button("🔒 Log Out"):
        for k in ["rep_logged_in", "rep_dept", "rep_year", "rep_name",
                  "rep_reg", "rep_ai_draft", "rep_ai_reply",
                  "pending_allocations", "rep_show_change_pw"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()