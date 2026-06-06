import streamlit as st
import pandas as pd
import io
from datetime import datetime
from database import SheetDatabaseManager
from cache import cached_fetch_materials, cached_fetch_announcements, cached_fetch_feedback, cached_fetch_rep_replies


def render_class_rep_interface(db: SheetDatabaseManager, ai, df_profiles):

    # ── Access control ────────────────────────────────────────
    if st.session_state.role != "Class Rep":
        st.warning("🔒 Access Denied. This panel is reserved for Class Representatives.")
        return

    if "class_rep_authenticated" not in st.session_state:
        st.session_state.class_rep_authenticated = False
    if "active_rep_name" not in st.session_state:
        st.session_state.active_rep_name = "Class Rep"
    if "confirm_logout" not in st.session_state:
        st.session_state.confirm_logout = False

    # ── Login screen ──────────────────────────────────────────
    if not st.session_state.class_rep_authenticated:
        st.title("🔐 Class Rep Authentication Portal")
        st.write("Enter your credentials to access the administrative dashboard.")

        input_reg = st.text_input("Registration Number:", placeholder="e.g., 25/U/08624/PS", key="rep_gate_reg").strip().upper()
        input_pin = st.text_input("Personal Security PIN:", type="password", key="rep_gate_pin")

        if st.button("🔓 Verify Identity & Access"):
            allowed_reps = st.secrets.get("CLASS_REPS", {})
            if input_reg in allowed_reps:
                if str(input_pin) == str(allowed_reps[input_reg]):
                    if not df_profiles.empty and input_reg in df_profiles['Reg Number'].astype(str).values:
                        student_row = df_profiles[df_profiles["Reg Number"] == input_reg].iloc[0]
                        st.session_state.active_rep_name = student_row["Student Name"]
                    else:
                        st.session_state.active_rep_name = f"Rep ({input_reg})"
                    st.session_state.class_rep_authenticated = True
                    st.success(f"✅ Access Granted! Welcome, {st.session_state.active_rep_name}.")
                    st.rerun()
                else:
                    st.error("❌ Invalid PIN. Verification failed.")
            else:
                st.error("❌ Registration Number not on the Class Rep whitelist.")
        return

    # ═════════════════════════════════════════════════════════
    # AUTHENTICATED DASHBOARD
    # ═════════════════════════════════════════════════════════
    st.title("👑 Class Representative Dashboard")
    st.write(f"🛡️ Active Session: **{st.session_state.active_rep_name}**")

    # ── Logout with confirmation ──────────────────────────────
    if not st.session_state.confirm_logout:
        if st.button("🔒 Close Session & Lock Dashboard"):
            st.session_state.confirm_logout = True
            st.rerun()
    else:
        st.warning("Are you sure you want to lock the dashboard?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, Lock"):
                st.session_state.class_rep_authenticated = False
                st.session_state.active_rep_name = "Class Rep"
                st.session_state.confirm_logout = False
                st.rerun()
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.confirm_logout = False
                st.rerun()

    st.markdown("---")

    # ═════════════════════════════════════════════════════════
    # SECTION 0: ANALYTICS
    # ═════════════════════════════════════════════════════════
    st.subheader("📊 Roster Demographics & Analytics")

    total_registered  = len(df_profiles)
    unassigned_count  = len(df_profiles[df_profiles["Assigned Group"].astype(str).str.strip() == "Unassigned"]) if total_registered > 0 else 0
    assigned_count    = total_registered - unassigned_count

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Registered", total_registered)
    m2.metric("Allocated to Teams", assigned_count)
    m3.metric("Pending Allocation", unassigned_count)

    if "Course Code" in df_profiles.columns and total_registered > 0:
        st.write("📈 **Enrollment Share per Programme:**")
        course_counts = df_profiles["Course Code"].value_counts().reset_index()
        course_counts.columns = ["Program Code", "Student Count"]
        st.bar_chart(data=course_counts, x="Program Code", y="Student Count", use_container_width=True)
        with st.expander("🔍 Exact numeric breakdown"):
            for _, row in course_counts.iterrows():
                pct = (row['Student Count'] / total_registered) * 100
                st.write(f"• **{row['Program Code']}:** {row['Student Count']} students ({pct:.1f}%)")
    else:
        st.info("No student data yet.")

    st.markdown("---")

    # ═════════════════════════════════════════════════════════
    # SECTION 1: REGISTERED STUDENTS
    # ═════════════════════════════════════════════════════════
    st.subheader("📋 Registered Students Registry")
    if st.button("👀 Show Registered Profiles"):
        live_roster = db.fetch_roster()
        if live_roster.empty:
            st.info("No students have registered yet.")
        else:
            live_roster = live_roster.reset_index(drop=True)
            live_roster.index = live_roster.index + 1
            st.dataframe(live_roster[["Student Name", "Reg Number", "Course Code", "Contact", "Assigned Group"]], use_container_width=True)
            st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            csv_data = live_roster.to_csv(index=True).encode("utf-8")
            st.download_button("⬇️ Download Roster (CSV)", data=csv_data, file_name="registered_students.csv", mime="text/csv")

            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                live_roster.to_excel(writer, index=True, sheet_name='Roster')
            st.download_button("⬇️ Download Roster (Excel)", data=excel_buffer.getvalue(), file_name="registered_students.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("---")

    # ═════════════════════════════════════════════════════════
    # SECTION 2: DELETE STUDENT (search by letter)
    # ═════════════════════════════════════════════════════════
    st.subheader("🗑️ Remove Student Record")

    search_letter = st.text_input("🔍 Search student by name or letter:", placeholder="e.g., type 'A' or 'Ali'", key="del_search")

    if search_letter.strip():
        matches = df_profiles[
            df_profiles["Student Name"].astype(str).str.lower().str.contains(search_letter.strip().lower())
        ]
        if not matches.empty:
            student_options = matches["Student Name"].tolist()
            selected_student = st.selectbox("Select student to delete:", student_options, key="del_select")

            if "confirm_delete_student" not in st.session_state:
                st.session_state.confirm_delete_student = False

            if not st.session_state.confirm_delete_student:
                if st.button("🗑️ Delete Selected Student", key="del_btn"):
                    st.session_state.confirm_delete_student = True
                    st.rerun()
            else:
                st.warning(f"⚠️ Are you sure you want to permanently delete **{selected_student}**?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Yes, Delete", key="del_confirm_yes"):
                        result = db.delete_student(selected_student)
                        if isinstance(result, dict) and result.get("status") == "success" or result is True:
                            st.success(f"✅ '{selected_student}' deleted successfully.")
                            st.session_state.confirm_delete_student = False
                            st.rerun()
                        else:
                            st.error("⚠️ Deletion failed. Please try again.")
                            st.session_state.confirm_delete_student = False
                with c2:
                    if st.button("❌ Cancel", key="del_confirm_no"):
                        st.session_state.confirm_delete_student = False
                        st.rerun()
        else:
            st.info(f"No students found matching '{search_letter}'.")

    st.markdown("---")

    # ═════════════════════════════════════════════════════════
    # SECTION 3: ANNOUNCEMENTS
    # ═════════════════════════════════════════════════════════
    st.subheader("📢 Class Announcements Noticeboard")
    with st.expander("📢 Post New Announcement", expanded=False):
        announcement_text = st.text_area("Announcement text:", key="class_rep_ann_area", placeholder="Type class broadcast details here...")
        priority_choice   = st.selectbox("Priority Level:", ["Normal", "Urgent"], key="ann_priority")

        if st.button("📤 Submit Announcement"):
            if announcement_text.strip():
                with st.spinner("Posting..."):
                    rep_signature  = st.session_state.get("active_rep_name", "Class Rep")
                    current_time   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    signed_text    = f"{announcement_text.strip()}\n\n✍️ — Posted by: {rep_signature} ({current_time})"
                    success        = db.post_announcement(signed_text, priority=priority_choice)
                    if success:
                        st.success(f"🎉 Announcement posted as **{priority_choice}**!")
                        st.rerun()
                    else:
                        st.error("⚠️ Failed to post announcement.")
            else:
                st.warning("Please enter some text before posting.")

        st.markdown("---")
        st.markdown("##### 📚 Current Announcements")
        live_announcements = db.fetch_announcements()

        # Session state for announcement delete confirmation
        if "confirm_del_ann" not in st.session_state:
            st.session_state.confirm_del_ann = None

        if live_announcements:
            for idx, ann in enumerate(live_announcements):
                timestamp  = ann.get("timestamp", "N/A")
                text       = ann.get("text", "")
                priority   = ann.get("priority", "Normal")
                badge      = "🔴 URGENT" if priority.lower() == "urgent" else "🟡 Normal"
                ann_key    = f"{idx}_{timestamp[:10]}"

                col1, col2 = st.columns([5, 1])
                with col1:
                    if priority.lower() == "urgent":
                        st.error(f"**{badge}** · {timestamp}\n\n{text}")
                    else:
                        st.info(f"**{badge}** · {timestamp}\n\n{text}")
                with col2:
                    if st.session_state.confirm_del_ann != ann_key:
                        if st.button("🗑️", key=f"del_ann_{ann_key}"):
                            st.session_state.confirm_del_ann = ann_key
                            st.rerun()
                    else:
                        st.warning("Sure?")
                        ca, cb = st.columns(2)
                        with ca:
                            if st.button("✅", key=f"ann_yes_{ann_key}"):
                                with st.spinner("Deleting..."):
                                    if db.delete_announcement(text.strip()):
                                        cached_fetch_announcements.clear()
                                        st.session_state.confirm_del_ann = None
                                        st.success("✅ Deleted.")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed.")
                                        st.session_state.confirm_del_ann = None
                        with cb:
                            if st.button("❌", key=f"ann_no_{ann_key}"):
                                st.session_state.confirm_del_ann = None
                                st.rerun()
        else:
            st.caption("No announcements yet.")

    st.markdown("---")

    # ═════════════════════════════════════════════════════════
    # SECTION 4: MATERIALS — upload + view + delete
    # ═════════════════════════════════════════════════════════
    st.subheader("📂 Course Materials")

    with st.expander("📤 Upload New Material", expanded=False):
        with st.form("upload_materials_form", clear_on_submit=True):
            uploaded_file = st.file_uploader("Choose a PDF file:", type=["pdf"])
            submit_file   = st.form_submit_button("📤 Upload to Cloud")
            if submit_file:
                if uploaded_file is not None:
                    with st.spinner(f"Uploading {uploaded_file.name}..."):
                        success = db.upload_material(uploaded_file.getvalue(), uploaded_file.name, "application/pdf")
                        if success:
                            st.success(f"🎉 {uploaded_file.name} uploaded successfully!")
                            st.rerun()
                        else:
                            st.error("⚠️ Upload failed. Check deployment link or file size.")
                else:
                    st.warning("Please select a PDF file first.")

    with st.expander("📁 View & Manage Uploaded Materials", expanded=False):
        materials_list = db.fetch_materials()
        if materials_list:
            st.write(f"**{len(materials_list)} file(s) uploaded:**")
            for midx, mat in enumerate(materials_list):
                file_name = mat.get("name", "Unnamed")
                file_url  = mat.get("url", "#")
                ext       = file_name.split(".")[-1].upper() if "." in file_name else "FILE"

                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    st.markdown(f"📄 **{file_name}**")
                with col2:
                    st.markdown(f"[🔗 View]({file_url})")
                with col3:
                    if st.button("🗑️", key=f"del_mat_{midx}_{file_name[:10]}"):
                        with st.spinner("Deleting..."):
                            if db.delete_material(file_name):
                                cached_fetch_materials.clear()
                                st.success(f"✅ '{file_name}' deleted.")
                                st.rerun()
                            else:
                                st.error("❌ Could not delete.")
                st.markdown("---")
        else:
            st.info("No materials uploaded yet.")

    st.markdown("---")

    # ═════════════════════════════════════════════════════════
    # SECTION 5: AI TEAM ALLOCATION
    # ═════════════════════════════════════════════════════════
    st.subheader("🤖 Project Squad Configuration")
    with st.expander("🤖 Open AI Team Allocation Panel", expanded=False):
        st.write("Configure parameters to let AI automatically distribute students into balanced project groups.")
        team_size    = st.slider("Target Students per Group:", 2, 6, 3)
        custom_rules = st.text_area("Custom Constraints (Optional):", placeholder="e.g., Mix BMEC and BPPE students evenly...")

        if st.button("🚀 Run AI Allocation Engine"):
            with st.spinner("AI is processing distributions..."):
                ai_output = ai.generate_teams(df_profiles, team_size, custom_rules)
                if "error" in ai_output:
                    st.error(f"AI Error: {ai_output['error']}")
                else:
                    sync_response = db.save_group_allocations(ai_output)
                    if sync_response.get("status") == "success":
                        st.success("🎉 Allocation complete! Teams written to Google Sheet.")
                        st.rerun()
                    else:
                        st.error("AI sorted but cloud transmission failed.")

    st.markdown("---")

    # ═════════════════════════════════════════════════════════
    # SECTION 6: TEAM ROSTERS
    # ═════════════════════════════════════════════════════════
    st.subheader("👥 Finalized Project Squads")
    if st.button("📂 Show Allocated Groups"):
        assigned_students = db.fetch_roster()
        assigned_students = assigned_students[assigned_students["Assigned Group"] != "Unassigned"]

        if assigned_students.empty:
            st.info("💡 No teams generated yet. Use the Allocation Engine above.")
        else:
            for group in sorted(assigned_students["Assigned Group"].unique()):
                with st.container():
                    st.markdown(f"### 👥 {group}")
                    group_members = assigned_students[assigned_students["Assigned Group"] == group].reset_index(drop=True)
                    group_members.index = group_members.index + 1
                    st.dataframe(group_members[["Student Name", "Course Code", "Contact"]], use_container_width=True)
                    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                    csv_group = group_members.to_csv(index=True).encode("utf-8")
                    st.download_button(f"⬇️ Download {group} (CSV)", data=csv_group, file_name=f"{group}_members.csv", mime="text/csv")

                    grp_buffer = io.BytesIO()
                    with pd.ExcelWriter(grp_buffer, engine='openpyxl') as writer:
                        group_members.to_excel(writer, index=True, sheet_name=str(group)[:30])
                    st.download_button(f"⬇️ Download {group} (Excel)", data=grp_buffer.getvalue(), file_name=f"{group}_members.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("---")

    # ═════════════════════════════════════════════════════════
    # SECTION 7: STUDENT FEEDBACK INBOX + REP REPLIES
    # ═════════════════════════════════════════════════════════
    st.subheader("📬 Student Feedback Inbox")
    with st.expander("📬 Open Student Messages Inbox", expanded=False):
        feedback_logs = db.fetch_feedback()

        # Session state for per-message delete confirmation
        if "confirm_del_fb" not in st.session_state:
            st.session_state.confirm_del_fb = None

        # Session state for reply panel — tracks which message is open for reply
        if "reply_open_for" not in st.session_state:
            st.session_state.reply_open_for = None

        if feedback_logs:
            st.write(f"**{len(feedback_logs)} message(s) in inbox:**")
            for fidx, fb in enumerate(feedback_logs):
                if isinstance(fb, list) and len(fb) >= 5:
                    msg_time   = str(fb[0]).strip()
                    msg_reg    = str(fb[1]).strip()
                    msg_name   = str(fb[2]).strip()
                    msg_status = str(fb[3]).strip()
                    msg_text   = str(fb[4]).strip()
                    msg_key    = f"{fidx}_{msg_reg}_{msg_time[:10]}"

                    is_reviewed  = msg_status.lower() == "reviewed"
                    status_color = "#16a34a" if is_reviewed else "#d4820a"
                    status_label = "✅ Reviewed" if is_reviewed else "⏳ Pending Review"

                    # ── Message card ──────────────────────────
                    st.markdown(f"""
                    <div style="background:{'#f0fdf4' if is_reviewed else '#fffbeb'};
                        border:1px solid {'#86efac' if is_reviewed else '#fcd34d'};
                        border-left:4px solid {status_color};
                        border-radius:10px; padding:14px 16px; margin-bottom:10px;">
                        <div style="font-size:0.78rem;color:#64748b;margin-bottom:4px;">
                            👤 <b>{msg_name}</b> · {msg_reg} · 🕐 {msg_time} ·
                            <span style="color:{status_color};font-weight:600;">{status_label}</span>
                        </div>
                        <div style="font-size:0.9rem;color:#1e293b;">{msg_text}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # ── Action buttons row ────────────────────
                    col1, col2, col3 = st.columns([1, 1, 1])

                    # Mark as Reviewed
                    with col1:
                        if not is_reviewed:
                            if st.button("✅ Mark Reviewed", key=f"rev_{msg_key}"):
                                with st.spinner("Updating..."):
                                    if db.update_feedback_status(msg_time, msg_reg, "Reviewed"):
                                        cached_fetch_feedback.clear()
                                        st.success("✅ Marked as reviewed.")
                                        st.rerun()
                                    else:
                                        st.error("❌ Update failed.")

                    # Reply button — toggles reply panel open/close
                    with col2:
                        reply_btn_label = "✉️ Close Reply" if st.session_state.reply_open_for == msg_key else "💬 Reply"
                        if st.button(reply_btn_label, key=f"reply_btn_{msg_key}"):
                            if st.session_state.reply_open_for == msg_key:
                                st.session_state.reply_open_for = None
                            else:
                                st.session_state.reply_open_for = msg_key
                            st.rerun()

                    # Delete button
                    with col3:
                        if st.session_state.confirm_del_fb != msg_key:
                            if st.button("🗑️ Delete", key=f"del_fb_{msg_key}"):
                                st.session_state.confirm_del_fb = msg_key
                                st.rerun()
                        else:
                            st.warning("Sure?")
                            ca, cb = st.columns(2)
                            with ca:
                                if st.button("✅", key=f"fb_yes_{msg_key}"):
                                    with st.spinner("Deleting..."):
                                        if db.delete_feedback(msg_time, msg_reg):
                                            cached_fetch_feedback.clear()
                                            st.session_state.confirm_del_fb = None
                                            st.success("✅ Deleted.")
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed.")
                                            st.session_state.confirm_del_fb = None
                            with cb:
                                if st.button("❌", key=f"fb_no_{msg_key}"):
                                    st.session_state.confirm_del_fb = None
                                    st.rerun()

                    # ── Inline reply panel ────────────────────
                    if st.session_state.reply_open_for == msg_key:
                        st.markdown(f"""
                        <div style="background:#eff6ff; border:1px solid #bfdbfe;
                            border-left:4px solid #3b82f6; border-radius:8px;
                            padding:12px 16px; margin-top:6px; margin-bottom:4px;">
                            <div style="font-size:0.8rem;color:#1d4ed8;font-weight:600;">
                                💬 Replying to: {msg_name} ({msg_reg})
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        reply_text = st.text_area(
                            "Your reply:",
                            placeholder=f"Type your reply to {msg_name} here...",
                            key=f"reply_text_{msg_key}",
                            height=100
                        )

                        send_col, cancel_col = st.columns([1, 1])
                        with send_col:
                            if st.button("📤 Send Reply", key=f"send_reply_{msg_key}"):
                                if reply_text.strip():
                                    rep_name = st.session_state.get("active_rep_name", "Class Rep")
                                    with st.spinner("Sending reply..."):
                                        ok = db.post_rep_reply(
                                            reg_number=msg_reg,
                                            student_name=msg_name,
                                            message=reply_text.strip(),
                                            rep_name=rep_name
                                        )
                                    if ok:
                                        # Also mark original message as reviewed
                                        db.update_feedback_status(msg_time, msg_reg, "Reviewed")
                                        cached_fetch_feedback.clear()
                                        cached_fetch_rep_replies.clear()
                                        st.session_state.reply_open_for = None
                                        st.success(f"✅ Reply sent to {msg_name}!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to send reply. Please try again.")
                                else:
                                    st.warning("Please type a reply before sending.")
                        with cancel_col:
                            if st.button("✖️ Cancel", key=f"cancel_reply_{msg_key}"):
                                st.session_state.reply_open_for = None
                                st.rerun()

                    st.markdown("---")
        else:
            st.caption("No messages yet.")

    st.markdown("---")

    # ═════════════════════════════════════════════════════════
    # SECTION 8: REP SENT REPLIES OVERVIEW
    # ═════════════════════════════════════════════════════════
    st.subheader("📤 Sent Replies Overview")
    with st.expander("📤 View All Replies Sent to Students", expanded=False):
        all_replies = db.fetch_rep_replies(reg_number=None)

        if all_replies:
            st.write(f"**{len(all_replies)} reply/replies sent:**")
            for ridx, reply in enumerate(all_replies):
                r_time    = reply.get("timestamp", "N/A")
                r_to_name = reply.get("student_name", "Unknown")
                r_to_reg  = reply.get("reg_number", "")
                r_msg     = reply.get("message", "")
                r_status  = reply.get("read_status", "Unread")

                is_read      = r_status.lower() == "read"
                badge_color  = "#16a34a" if is_read else "#64748b"
                badge_label  = "👁️ Read" if is_read else "📭 Unread"

                st.markdown(f"""
                <div style="background:{'#f0fdf4' if is_read else '#f8fafc'};
                    border:1px solid {'#86efac' if is_read else '#cbd5e1'};
                    border-left:4px solid {badge_color};
                    border-radius:10px; padding:12px 16px; margin-bottom:8px;">
                    <div style="font-size:0.78rem;color:#64748b;margin-bottom:4px;">
                        📨 To: <b>{r_to_name}</b> · {r_to_reg} · 🕐 {r_time} ·
                        <span style="color:{badge_color};font-weight:600;">{badge_label}</span>
                    </div>
                    <div style="font-size:0.9rem;color:#1e293b;">{r_msg}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No replies sent yet.")
