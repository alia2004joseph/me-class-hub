"""
superadmin.py — Super Admin Dashboard.
Full rep management from the UI — no secrets.toml needed.
Sees all departments and years, can broadcast, manage reps, view all data.
"""
import streamlit as st
import pandas as pd
from database import SheetDatabaseManager
from ai_engine import AIAdminAssistant
from config import get_departments, YEARS, get_dept_codes, dept_color, dept_light, dept_name, COLOUR_PALETTE, load_departments


ADMIN_PRIMARY = "#0f172a"
ADMIN_ACCENT  = "#6d28d9"
ADMIN_LIGHT   = "#ede9fe"


def inject_admin_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    html,body,[class*="css"]{{font-family:'Plus Jakarta Sans',sans-serif;}}
    #MainMenu,footer{{visibility:hidden;}}
    .stApp{{background:#F0F4FF;}}
    .admin-banner{{
        background:linear-gradient(135deg,{ADMIN_PRIMARY} 0%,{ADMIN_ACCENT} 100%);
        border-radius:18px;padding:28px 32px;margin-bottom:24px;color:white;
    }}
    .admin-banner h2{{font-size:1.7rem;font-weight:800;margin:0 0 6px 0;color:white;}}
    .dept-card{{
        background:white;border-radius:14px;padding:20px;
        border:1px solid #e2e8f7;border-top:4px solid var(--dc);
        box-shadow:0 2px 8px rgba(0,0,0,0.05);margin-bottom:8px;
    }}
    .admin-pill{{
        display:inline-block;background:rgba(255,255,255,0.15);
        border:1px solid rgba(255,255,255,0.25);border-radius:20px;
        padding:4px 14px;font-size:0.75rem;font-weight:600;color:white;margin-right:6px;
    }}
    .rep-row{{
        background:white;border-radius:12px;padding:14px 18px;margin-bottom:8px;
        border:1px solid #e2e8f7;border-left:4px solid {ADMIN_ACCENT};
        display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;
    }}
    .rep-row .rr-info{{font-size:0.9rem;color:#1e293b;font-weight:600;}}
    .rep-row .rr-meta{{font-size:0.78rem;color:#94a3b8;margin-top:2px;}}
    .pro-divider{{height:1px;background:#e2e8f7;margin:22px 0;}}
    /* Pill-style tabs */
    .stTabs [data-baseweb="tab-list"]{{
        gap:4px;background:white;border-radius:12px;padding:4px;
        border:1px solid #e2e8f7;flex-wrap:wrap;
    }}
    .stTabs [data-baseweb="tab"]{{
        border-radius:8px;padding:8px 16px;font-weight:600;
        font-size:0.82rem;color:#64748b;background:transparent;border:none;
    }}
    .stTabs [aria-selected="true"]{{background:{ADMIN_ACCENT} !important;color:white !important;}}
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"]{{display:none;}}
    </style>
    """, unsafe_allow_html=True)


def render_superadmin_interface(db: SheetDatabaseManager, ai_admin: AIAdminAssistant):

    # ── Session init ─────────────────────────────────────────
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    st.title("🛡️ Super Admin Dashboard")
    st.markdown("---")

    # ════════════════════════════════════════════════════════
    # LOGIN
    # ════════════════════════════════════════════════════════
    if not st.session_state.admin_logged_in:
        st.subheader("🔐 Super Admin Login")
        password = st.text_input("Admin Password", type="password")
        if st.button("🔓 Log In", use_container_width=True):
            correct = st.secrets.get("SUPER_ADMIN_PASSWORD", "")
            if not correct:
                st.error("❌ No admin password set. Add SUPER_ADMIN_PASSWORD to secrets.toml.")
            elif password == correct:
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("❌ Incorrect password.")
        return

    inject_admin_css()

    # ── Fetch all data ────────────────────────────────────────
    df_all       = db.fetch_all_roster()
    all_feedback = db.fetch_all_feedback()
    all_anns     = db.fetch_all_announcements()
    reps_list    = db.fetch_reps()

    total_students = len(df_all) if not df_all.empty else 0
    total_feedback = len(all_feedback)
    total_depts    = len(get_departments())

    # ── Banner ────────────────────────────────────────────────
    st.markdown(f"""
    <div class="admin-banner">
        <h2>🛡️ Super Admin — University Overview</h2>
        <p style="opacity:0.75;margin:0 0 12px 0;">
            Manage all departments, year groups and class rep accounts.
        </p>
        <span class="admin-pill">🏛️ {total_depts} Departments</span>
        <span class="admin-pill">👥 {total_students} Students</span>
        <span class="admin-pill">📬 {total_feedback} Feedback Messages</span>
        <span class="admin-pill">👑 {len(reps_list)} Rep Accounts</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────
    tabs = st.tabs([
        "🏠 Overview", "🏛️ Departments", "👑 Manage Reps",
        "📢 Broadcast", "👥 All Students",
        "📬 All Feedback", "🤖 AI Insights"
    ])

    # ════════════════════════════════════════
    # 🏠 OVERVIEW
    # ════════════════════════════════════════
    with tabs[0]:
        st.markdown("### 🏠 Department Overview")

        cols = st.columns(len(get_departments()))
        for ci, (code, info) in enumerate(get_departments().items()):
            with cols[ci]:
                dept_count = 0
                if not df_all.empty:
                    for col in ["Department", "department", "dept"]:
                        if col in df_all.columns:
                            dept_count = len(df_all[df_all[col] == code])
                            break
                color = info["color"]
                st.markdown(f"""
                <div class="dept-card" style="--dc:{color};">
                    <div style="font-size:0.78rem;font-weight:700;color:#94a3b8;
                        text-transform:uppercase;letter-spacing:1px;">{code}</div>
                    <div style="font-size:1.4rem;font-weight:900;color:{color};
                        margin:4px 0;">{dept_count}</div>
                    <div style="font-size:0.78rem;color:#1e293b;">{info['name']}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        # Enrollment pivot table
        st.markdown("### 📊 Enrollment by Department × Year")
        if not df_all.empty:
            dept_col = next((c for c in ["Department","department","dept"]
                             if c in df_all.columns), None)
            year_col = next((c for c in ["Year","year"] if c in df_all.columns), None)
            if dept_col and year_col:
                pivot = df_all.groupby([dept_col, year_col]).size().unstack(fill_value=0)
                st.dataframe(pivot, use_container_width=True)
            else:
                st.info("Department/Year columns not yet populated in the roster.")
        else:
            st.info("No enrollment data yet.")

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        # Rep coverage table
        st.markdown("### 👑 Rep Coverage")
        rep_map = {}
        for r in reps_list:
            d = str(r.get("dept", r.get("department", ""))).strip().upper()
            y = str(r.get("year", "")).strip()
            n = str(r.get("rep_name", r.get("name", ""))).strip()
            rep_map[(d, y)] = n

        coverage_rows = []
        for code in get_dept_codes():
            for year in YEARS:
                rep = rep_map.get((code, year), "")
                coverage_rows.append({
                    "Department": dept_name(code),
                    "Year":       year,
                    "Rep":        rep if rep else "⚠️ Not assigned",
                    "Status":     "✅" if rep else "❌"
                })
        st.dataframe(pd.DataFrame(coverage_rows), use_container_width=True)


    # ════════════════════════════════════════
    # 🏛️ DEPARTMENTS
    # ════════════════════════════════════════
    with tabs[1]:
        st.markdown("### 🏛️ Manage Departments")
        depts = get_departments()

        # ── Add / Edit ───────────────────────────────────────
        st.markdown("#### ➕ Add New Department")
        with st.form("add_dept_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_code = st.text_input("Department Code", placeholder="e.g. CVL",
                    help="Short uppercase code — cannot be changed later")
                new_name = st.text_input("Full Name", placeholder="e.g. Civil Engineering")
            with col2:
                new_courses = st.text_input("Course Codes (comma separated)",
                    placeholder="e.g. BCIV,BSTR,BENV")

            # Colour palette picker
            st.markdown("**Pick a Colour:**")
            palette_cols = st.columns(len(COLOUR_PALETTE))
            selected_color = COLOUR_PALETTE[0]["hex"]
            selected_light = COLOUR_PALETTE[0]["light"]
            for pi, pal in enumerate(COLOUR_PALETTE):
                with palette_cols[pi]:
                    st.markdown(f"""
                    <div style="width:28px;height:28px;border-radius:50%;
                        background:{pal['hex']};margin:0 auto;
                        border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.2);"
                        title="{pal['name']}"></div>
                    <div style="font-size:0.6rem;text-align:center;color:#94a3b8;margin-top:2px;">
                        {pal['name']}
                    </div>
                    """, unsafe_allow_html=True)

            colour_names = [p["name"] for p in COLOUR_PALETTE]
            chosen_colour = st.selectbox("Select Colour", colour_names, key="new_dept_colour")
            chosen_pal    = next(p for p in COLOUR_PALETTE if p["name"] == chosen_colour)

            if st.form_submit_button("✅ Add Department", use_container_width=True):
                if not new_code or not new_name or not new_courses:
                    st.warning("Please fill in all fields.")
                elif new_code.strip().upper() in depts:
                    st.error(f"❌ Department code '{new_code.upper()}' already exists.")
                else:
                    with st.spinner("Adding..."):
                        ok = db.add_department(
                            new_code, new_name,
                            chosen_pal["hex"], chosen_pal["light"], new_courses
                        )
                    if ok:
                        st.success(f"✅ Department '{new_name}' added!")
                        st.rerun()
                    else:
                        st.error("❌ Failed. Check your GAS deployment.")

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        # ── Current departments ──────────────────────────────
        st.markdown("#### 📋 Current Departments")
        if not depts:
            st.info("No departments loaded.")
        else:
            for didx, (code, info) in enumerate(depts.items()):
                color   = info.get("color", "#1a56db")
                lcolor  = info.get("light", "#dbeafe")
                dname   = info.get("name",  code)
                courses = ", ".join(info.get("courses", []))

                # Count students in this dept
                student_count = 0
                if not df_all.empty:
                    dcol = next((c for c in ["Department","department","dept"]
                                 if c in df_all.columns), None)
                    if dcol:
                        student_count = len(df_all[df_all[dcol] == code])

                with st.expander(f"🏛️ {dname} ({code}) — {student_count} students"):
                    # Edit form
                    with st.form(f"edit_dept_{code}"):
                        e_name    = st.text_input("Full Name",    value=dname)
                        e_courses = st.text_input("Course Codes", value=courses,
                            help="Comma separated, e.g. BMEC,BBPE")

                        st.markdown("**Change Colour:**")
                        e_colour_name = st.selectbox(
                            "Colour", [p["name"] for p in COLOUR_PALETTE],
                            index=next((i for i,p in enumerate(COLOUR_PALETTE)
                                        if p["hex"]==color), 0),
                            key=f"edit_col_{code}"
                        )
                        e_pal = next(p for p in COLOUR_PALETTE if p["name"] == e_colour_name)

                        # Preview swatch
                        st.markdown(f"""
                        <div style="display:flex;align-items:center;gap:10px;margin:8px 0;">
                            <div style="width:24px;height:24px;border-radius:50%;
                                background:{e_pal['hex']};border:2px solid white;
                                box-shadow:0 1px 4px rgba(0,0,0,0.2);"></div>
                            <span style="font-size:0.85rem;color:#475569;">
                                Preview: {e_pal['name']}
                            </span>
                        </div>
                        """, unsafe_allow_html=True)

                        sc1, sc2 = st.columns(2)
                        with sc1:
                            if st.form_submit_button("💾 Save Changes", use_container_width=True):
                                with st.spinner("Saving..."):
                                    ok = db.update_department(
                                        code, e_name, e_pal["hex"],
                                        e_pal["light"], e_courses
                                    )
                                if ok:
                                    st.success("✅ Updated!")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed.")
                        with sc2:
                            if st.form_submit_button("🗑️ Delete", use_container_width=True,
                                                      type="secondary"):
                                st.session_state[f"confirm_del_dept_{code}"] = True
                                st.rerun()

                    # Confirm delete
                    if st.session_state.get(f"confirm_del_dept_{code}"):
                        if student_count > 0:
                            st.error(
                                f"❌ Cannot delete **{dname}** — "
                                f"**{student_count} student(s)** are registered here. "
                                f"Transfer or remove all {code} students first."
                            )
                            if st.button("OK", key=f"ok_block_{code}"):
                                st.session_state[f"confirm_del_dept_{code}"] = False
                                st.rerun()
                        else:
                            st.warning(f"⚠️ Delete **{dname} ({code})**? This cannot be undone.")
                            da, db_ = st.columns(2)
                            with da:
                                if st.button("✅ Yes, delete", key=f"yes_dept_{code}"):
                                    with st.spinner("Deleting..."):
                                        result = db.delete_department(code)
                                    if result.get("status") == "success":
                                        st.session_state[f"confirm_del_dept_{code}"] = False
                                        st.success(f"✅ {dname} deleted.")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {result.get('message','Failed')}")
                            with db_:
                                if st.button("❌ Cancel", key=f"no_dept_{code}"):
                                    st.session_state[f"confirm_del_dept_{code}"] = False
                                    st.rerun()

    # ════════════════════════════════════════
    # 👑 MANAGE REPS
    # ════════════════════════════════════════
    with tabs[2]:
        st.markdown("### 👑 Class Rep Accounts")
        st.info(
            "Create or update a rep account here. "
            "The rep uses their department, year and password to log in — "
            "no code changes needed."
        )

        # ── Create / Update rep ──────────────────────────────
        st.markdown("#### ➕ Create or Update Rep Account")
        with st.form("assign_rep_form", clear_on_submit=True):
            dept_opts = {f"{v['name']} ({k})": k for k, v in get_departments().items()}
            d_label   = st.selectbox("Department", list(dept_opts.keys()), key="ar_dept")
            sel_dept  = dept_opts[d_label]
            sel_year  = st.selectbox("Year Group", YEARS, key="ar_year")

            rep_name  = st.text_input("Rep Full Name",    placeholder="e.g., Alice Nakamura")
            rep_reg   = st.text_input("Rep Reg Number",   placeholder="e.g., 25/U/0001/PS")
            rep_pw    = st.text_input(
                "Set Password",
                type="password",
                placeholder="Min 6 characters",
                help="The rep will use this to log in. They can change it later."
            )
            rep_pw2   = st.text_input("Confirm Password", type="password")

            submitted = st.form_submit_button("✅ Save Rep Account", use_container_width=True)

            if submitted:
                if not rep_name or not rep_reg or not rep_pw:
                    st.warning("Please fill in all fields.")
                elif rep_pw != rep_pw2:
                    st.error("❌ Passwords do not match.")
                elif len(rep_pw) < 6:
                    st.error("❌ Password must be at least 6 characters.")
                else:
                    with st.spinner("Saving..."):
                        ok = db.assign_rep(sel_dept, sel_year, rep_name, rep_reg, rep_pw)
                    if ok:
                        st.success(
                            f"✅ Rep account saved: **{rep_name}** → "
                            f"{dept_name(sel_dept)} — {sel_year}"
                        )
                        st.rerun()
                    else:
                        st.error("❌ Failed to save. Check your GAS deployment.")

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        # ── Current rep accounts ─────────────────────────────
        st.markdown("#### 📋 Current Rep Accounts")
        if not reps_list:
            st.info("No rep accounts created yet.")
        else:
            for ridx, rep in enumerate(reps_list):
                r_dept_code = str(rep.get("dept", rep.get("department", ""))).strip().upper()
                r_year      = str(rep.get("year", "")).strip()
                r_name      = str(rep.get("rep_name", rep.get("name", ""))).strip()
                r_reg       = str(rep.get("rep_reg",  rep.get("reg",  ""))).strip()
                r_has_pw    = rep.get("has_password", False)
                color       = dept_color(r_dept_code) if r_dept_code in get_departments() else ADMIN_ACCENT

                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"""
                    <div class="rep-row" style="border-left-color:{color};">
                        <div>
                            <div class="rr-info">
                                👑 {r_name}
                                <span style="background:{dept_light(r_dept_code) if r_dept_code in get_departments() else ADMIN_LIGHT};
                                    color:{color};font-size:0.7rem;font-weight:700;
                                    padding:2px 8px;border-radius:10px;margin-left:8px;">
                                    {r_dept_code} · {r_year}
                                </span>
                            </div>
                            <div class="rr-meta">
                                {dept_name(r_dept_code)} &nbsp;·&nbsp;
                                Reg: {r_reg} &nbsp;·&nbsp;
                                Password: {'✅ Set' if r_has_pw else '⚠️ Not set'}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button("🗑️ Remove", key=f"del_rep_{ridx}"):
                        st.session_state[f"confirm_del_rep_{ridx}"] = True
                        st.rerun()

                # Confirm delete
                if st.session_state.get(f"confirm_del_rep_{ridx}"):
                    st.warning(f"⚠️ Remove **{r_name}** ({r_dept_code} {r_year})? This cannot be undone.")
                    ca, cb = st.columns(2)
                    with ca:
                        if st.button("✅ Yes, remove", key=f"yes_del_{ridx}"):
                            with st.spinner("Removing..."):
                                ok = db.delete_rep(r_dept_code, r_year)
                            if ok:
                                st.session_state[f"confirm_del_rep_{ridx}"] = False
                                st.success("✅ Rep account removed.")
                                st.rerun()
                            else:
                                st.error("❌ Failed.")
                    with cb:
                        if st.button("❌ Cancel", key=f"no_del_{ridx}"):
                            st.session_state[f"confirm_del_rep_{ridx}"] = False
                            st.rerun()

        st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)

        # ── Reset a rep's password ───────────────────────────
        st.markdown("#### 🔑 Reset a Rep's Password")
        st.caption("Use this if a rep is locked out and needs their password reset.")

        if reps_list:
            rep_labels = {
                f"{r.get('rep_name','')} — {r.get('dept','')} {r.get('year','')}": r
                for r in reps_list
            }
            sel_rep_label = st.selectbox(
                "Select Rep", ["— Select —"] + list(rep_labels.keys()),
                key="reset_pw_sel"
            )
            if sel_rep_label != "— Select —":
                sel_rep = rep_labels[sel_rep_label]
                with st.form("reset_pw_form", clear_on_submit=True):
                    new_pw  = st.text_input("New Password",      type="password")
                    new_pw2 = st.text_input("Confirm Password",  type="password")
                    if st.form_submit_button("🔑 Reset Password", use_container_width=True):
                        if not new_pw:
                            st.warning("Please enter a new password.")
                        elif new_pw != new_pw2:
                            st.error("❌ Passwords do not match.")
                        elif len(new_pw) < 6:
                            st.error("❌ Must be at least 6 characters.")
                        else:
                            # Admin resets by re-assigning with new password
                            # We use assignRep which updates existing record
                            with st.spinner("Resetting..."):
                                ok = db.assign_rep(
                                    dept     = str(sel_rep.get("dept","")).upper(),
                                    year     = str(sel_rep.get("year","")),
                                    rep_name = str(sel_rep.get("rep_name","")),
                                    rep_reg  = str(sel_rep.get("rep_reg","")),
                                    password = new_pw
                                )
                            if ok:
                                st.success(f"✅ Password reset for {sel_rep.get('rep_name','')}.")
                            else:
                                st.error("❌ Reset failed.")
        else:
            st.info("No rep accounts to reset yet.")

    # ════════════════════════════════════════
    # 📢 BROADCAST
    # ════════════════════════════════════════
    with tabs[3]:
        st.markdown("### 📢 Broadcast Announcement")
        st.info(
            "Broadcasts appear for **all students** across all departments and years, "
            "marked as 🌐 BROADCAST."
        )

        with st.form("broadcast_form", clear_on_submit=True):
            b_text     = st.text_area("Announcement text", height=140)
            b_priority = st.selectbox("Priority", ["Normal", "Urgent"])
            c1, c2     = st.columns(2)
            with c1: post_btn  = st.form_submit_button("📢 Broadcast Now",  use_container_width=True)
            with c2: draft_btn = st.form_submit_button("✍️ Draft with AI", use_container_width=True)

            if draft_btn and b_text.strip():
                with st.spinner("Drafting..."):
                    st.session_state["admin_draft"] = ai_admin.generate_broadcast(
                        b_text, b_priority
                    )
            if post_btn:
                if b_text.strip():
                    if db.broadcast_announcement(b_text, b_priority):
                        st.success("✅ Broadcast sent to all departments!")
                        st.rerun()
                    else:
                        st.error("❌ Failed.")
                else:
                    st.warning("Please enter announcement text.")

        if st.session_state.get("admin_draft"):
            st.markdown("**AI Draft — edit before posting:**")
            edited = st.text_area("", value=st.session_state["admin_draft"], height=150)
            pri2   = st.selectbox("Priority", ["Normal", "Urgent"], key="bc_pri2")
            if st.button("📢 Post this Broadcast"):
                if db.broadcast_announcement(edited, pri2):
                    st.session_state["admin_draft"] = ""
                    st.success("✅ Broadcast posted!")
                    st.rerun()

        st.markdown("---")
        st.markdown("#### 📋 Recent Broadcasts")
        broadcasts = [
            a for a in all_anns
            if isinstance(a, dict) and a.get("dept", "") == "ALL"
        ]
        if broadcasts:
            for ann in broadcasts[:10]:
                st.markdown(f"""
                <div style="background:white;border-radius:10px;padding:12px 16px;
                    margin-bottom:8px;border:1px solid #e2e8f7;
                    border-left:4px solid {ADMIN_ACCENT};">
                    <div style="font-size:0.75rem;color:#94a3b8;">
                        🕐 {ann.get('timestamp','')} · 🌐 ALL DEPTS
                    </div>
                    <div style="margin-top:4px;">{ann.get('text','')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No broadcasts sent yet.")

    # ════════════════════════════════════════
    # 👥 ALL STUDENTS
    # ════════════════════════════════════════
    with tabs[4]:
        st.markdown("### 👥 All Registered Students")
        if df_all.empty:
            st.info("No students registered yet.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1: f_dept   = st.selectbox("Dept",   ["ALL"] + get_dept_codes(), key="f_dept")
            with c2: f_year   = st.selectbox("Year",   ["ALL"] + YEARS,      key="f_year")
            with c3: f_search = st.text_input("Search name/reg",              key="f_search")

            df_show = df_all.copy()

            # Normalise column names for filtering
            col_rename = {}
            for c in df_show.columns:
                if c.lower() in ("department", "dept", "dep"):
                    col_rename[c] = "Department"
                elif c.lower() == "year":
                    col_rename[c] = "Year"
            df_show = df_show.rename(columns=col_rename)

            if f_dept != "ALL" and "Department" in df_show.columns:
                df_show = df_show[df_show["Department"] == f_dept]
            if f_year != "ALL" and "Year" in df_show.columns:
                df_show = df_show[df_show["Year"] == f_year]
            if f_search:
                mask = (
                    df_show["Student Name"].str.contains(f_search, case=False, na=False) |
                    df_show["Reg Number"].str.contains(f_search,   case=False, na=False)
                )
                df_show = df_show[mask]

            st.caption(f"Showing {len(df_show)} of {total_students} students")
            st.dataframe(df_show, use_container_width=True)

            csv = df_show.to_csv(index=False)
            st.download_button(
                "⬇️ Export to CSV", data=csv,
                file_name="students.csv", mime="text/csv"
            )

    # ════════════════════════════════════════
    # 📬 ALL FEEDBACK
    # ════════════════════════════════════════
    with tabs[5]:
        st.markdown("### 📬 All Student Feedback")
        if not all_feedback:
            st.info("No feedback messages yet.")
        else:
            f_dept2 = st.selectbox("Filter by Dept", ["ALL"] + get_dept_codes(), key="fb_dept")

            filtered_fb = all_feedback
            if f_dept2 != "ALL":
                filtered_fb = [
                    f for f in all_feedback
                    if isinstance(f, list) and len(f) >= 6
                    and str(f[5]).strip().upper() == f_dept2
                ]

            st.caption(f"{len(filtered_fb)} messages")

            for fb in filtered_fb[:50]:
                if not (isinstance(fb, list) and len(fb) >= 5):
                    continue
                ts       = str(fb[0])
                reg      = str(fb[1])
                name     = str(fb[2])
                status   = str(fb[3])
                msg      = str(fb[4])
                dept_fb  = str(fb[5]).strip().upper() if len(fb) > 5 else "?"
                year_fb  = str(fb[6]).strip()         if len(fb) > 6 else "?"
                sc       = "#16a34a" if status.lower() == "reviewed" else "#d4820a"
                color    = dept_color(dept_fb) if dept_fb in get_departments() else ADMIN_ACCENT

                st.markdown(f"""
                <div style="background:white;border-radius:10px;padding:12px 16px;
                    margin-bottom:8px;border:1px solid #e2e8f7;border-left:4px solid {color};">
                    <div style="font-size:0.75rem;color:#94a3b8;">
                        👤 <strong>{name}</strong> · {reg}
                        &nbsp;·&nbsp;
                        <span style="background:{dept_color(dept_fb) if dept_fb in get_departments() else '#e2e8f7'};
                            color:white;font-size:0.68rem;font-weight:700;
                            padding:1px 7px;border-radius:8px;">{dept_fb}</span>
                        {year_fb} · 🕐 {ts}
                        &nbsp;<span style="color:{sc};font-weight:600;">{status}</span>
                    </div>
                    <div style="margin-top:6px;font-size:0.9rem;">{msg}</div>
                </div>
                """, unsafe_allow_html=True)

    # ════════════════════════════════════════
    # 🤖 AI INSIGHTS
    # ════════════════════════════════════════
    with tabs[6]:
        st.markdown("### 🤖 AI-Powered Insights")

        insight = st.radio("Choose:", [
            "📊 Enrollment Analysis",
            "📬 Feedback Summary",
        ], horizontal=True)

        if insight == "📊 Enrollment Analysis":
            if st.button("📊 Analyse Enrollment", use_container_width=True):
                with st.spinner("Analysing..."):
                    result = ai_admin.analyze_enrollment(df_all)
                st.markdown(result)

        elif insight == "📬 Feedback Summary":
            f_dept3 = st.selectbox("Scope", ["ALL"] + get_dept_codes(), key="ai_fb_dept")
            if st.button("📬 Summarize Feedback", use_container_width=True):
                if f_dept3 == "ALL":
                    fb_scope = all_feedback
                else:
                    fb_scope = [
                        f for f in all_feedback
                        if isinstance(f, list) and len(f) > 5
                        and str(f[5]).strip().upper() == f_dept3
                    ]
                with st.spinner("Analysing..."):
                    result = ai_admin.summarize_all_feedback(fb_scope, f_dept3)
                st.markdown(result)

    # ── Logout ────────────────────────────────────────────────
    st.markdown('<div class="pro-divider"></div>', unsafe_allow_html=True)
    if st.button("🔒 Log Out"):
        st.session_state.admin_logged_in = False
        for k in ["admin_draft"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()