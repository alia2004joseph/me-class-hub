import streamlit as st
import pandas as pd
import io  # Required for safe browser-direct memory downloads [1.1]
from datetime import datetime
from database import SheetDatabaseManager   # Imports your shared database connector class

  

def render_class_rep_interface(db: SheetDatabaseManager, ai, df_profiles):
    # 1. Access control role verification layer
    if st.session_state.role != "Class Rep":
        st.warning("🔒 Access Denied. This panel is reserved for Class Representatives.")
        return

    # Initialize session state cache tracking parameters if missing
    if "class_rep_authenticated" not in st.session_state:
        st.session_state.class_rep_authenticated = False
    if "active_rep_name" not in st.session_state:
        st.session_state.active_rep_name = "Class Rep"

    # 2. IF NOT AUTHENTICATED: Draw the secure Multi-User login screen
    if not st.session_state.class_rep_authenticated:
        st.title("🔐 Class Rep Authentication Portal")
        st.write("Enter your unique individual credentials to access the administrative control center dashboard.")
        
        # Collect credentials
        input_reg = st.text_input("Enter Your Registration Number:", placeholder="e.g., 25/U/08624/PS", key="rep_gate_reg").strip().upper()
        input_pin = st.text_input("Enter Your Personal Security PIN:", type="password", key="rep_gate_pin")
        
        if st.button("🔓 Verify Identity & Access"):
            # Fetch the entire whitelisted dictionary from secrets scope [1.1]
            allowed_reps = st.secrets.get("CLASS_REPS", {})
            
            # Check 1: Is the typed registration ID present in our whitelist?
            if input_reg in allowed_reps:
                # Check 2: Does the typed PIN match the assigned value for that ID?
                if str(input_pin) == str(allowed_reps[input_reg]):
                    
                    # Look up their actual human name from the live student roster to welcome them
                    if not df_profiles.empty and input_reg in df_profiles['Reg Number'].astype(str).values:
                        student_row = df_profiles[df_profiles["Reg Number"] == input_reg].iloc[0]
                        st.session_state.active_rep_name = student_row["Student Name"]
                    else:
                        st.session_state.active_rep_name = f"Rep ({input_reg})"
                        
                    st.session_state.class_rep_authenticated = True
                    st.success(f"✅ Access Granted! Welcome back, {st.session_state.active_rep_name}.")
                    st.rerun()
                else:
                    st.error("❌ Invalid PIN Code sequence. Verification failed.")
            else:
                st.error("❌ Registration Number is not registered on the Class Rep administrative whitelist.")
        
        # Force block stop execution so unauthorized users cannot scan the dashboard code components
        return

    # =========================================================================
    # 3. IF AUTHENTICATED: LOAD THE FULL CONTROL CENTER REGISTERED FUNCTIONS BELOW
    # =========================================================================
    st.title("👑 Class Representative Dashboard")
    
    # Personalised greetings layout block
    st.write(f"🛡️ Active Admin Session: **{st.session_state.active_rep_name}**")
    
    if st.button("🔒 Close Session & Lock Dashboard"):
        st.session_state.class_rep_authenticated = False
        st.session_state.active_rep_name = "Class Rep"
        st.rerun()
        
    st.markdown("---")

       # =========================================================
    # UPGRADE B: LIVE ROSTER REGISTRATION ANALYTICS DASHBOARD
    # =========================================================
    st.subheader("📊 Roster Demographics & Analytics")
    
    # 1. Calculate Summary Metrics Rows Layout
    total_registered = len(df_profiles)
    
    # Filter using string checks to capture who is fully allocated vs unassigned
    unassigned_count = len(df_profiles[df_profiles["Assigned Group"].astype(str).str.strip() == "Unassigned"]) if total_registered > 0 else 0
    assigned_count = total_registered - unassigned_count
    
    # Render interactive metrics KPI metric columns cards
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Profiles Registered", total_registered)
    m2.metric("Students Allocated to Teams", assigned_count)
    m3.metric("Students Pending Allocation", unassigned_count)
    
    # 2. Draw Visual Course Code Demographics Proportional Bar Charts Layout
    if "Course Code" in df_profiles.columns and total_registered > 0:
        st.write("📈 **Current Enrollment Share per Program Code:**")
        
        # Pull raw counts of each engineering code category tracking cell
        course_counts = df_profiles["Course Code"].value_counts().reset_index()
        course_counts.columns = ["Program Code", "Student Count"]
        
        # Display as a clean, interactive Streamlit native Bar Chart layout
        st.bar_chart(
            data=course_counts,
            x="Program Code",
            y="Student Count",
            use_container_width=True
        )
        
        # Display a quick proportional numeric numeric list data breakdown guide
        with st.expander("🔍 Click to inspect exact numeric distributions"):
            for _, row in course_counts.iterrows():
                percentage = (row['Student Count'] / total_registered) * 100
                st.write(f"• **{row['Program Code']}:** {row['Student Count']} students ({percentage:.1f}%)")
    else:
        st.info("Waiting for student profiles data to compile dashboard charts metrics panels.")
        
    st.markdown("---")

        
  

   
    # =========================================================
    # SECTION 1: VIEW REGISTERED STUDENTS (INTERACTIVE DATAFRAME)
    # =========================================================
    st.subheader("📋 Registered Students Registry")
    if st.button("👀 Show Registered Profiles"):
        live_roster = db.fetch_roster()   # Pull fresh data records live from your Google Sheet
        if live_roster.empty:
            st.info("No students have registered yet.")
        else:
            live_roster = live_roster.reset_index(drop=True)
            live_roster.index = live_roster.index + 1
            
            # Use st.dataframe to instantly restore zoom, search, and row expansions
            st.dataframe(
                live_roster[["Student Name", "Reg Number", "Course Code", "Contact", "Assigned Group"]], 
                use_container_width=True
            )

            st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Standard CSV Export
            csv_data = live_roster.to_csv(index=True).encode("utf-8")
            st.download_button("⬇️ Download Full Roster (CSV)", data=csv_data, file_name="registered_students.csv", mime="text/csv")

            # In-Memory Excel Generation (Bypasses Server Storage Block) [1.1]
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                live_roster.to_excel(writer, index=True, sheet_name='Roster')
            
            st.download_button(
                label="⬇️ Download Full Roster (Excel)",
                data=excel_buffer.getvalue(),
                file_name="registered_students.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    st.markdown("---")

        # =========================================================
    # SECTION 2: POST ANNOUNCEMENTS (WITH ADMIN SIGNATURES)
    # =========================================================
    st.subheader("📢 Class Announcements Noticeboard")
    with st.expander("📢 Open Make Announcements Panel", expanded=False):
        st.write("Post notices, deadlines, or project guidelines here. Logged-in students will see this inside their accounts.")
        
        # New Announcement Form Input Field Box Block 
        announcement_text = st.text_area("Enter a new announcement text:", key="class_rep_ann_area", placeholder="Type class broadcast details here...")
        
        if st.button("📤 Submit Announcement"):
            if announcement_text.strip():
                with st.spinner("Posting to database..."):
                    # Extract the human name of the currently logged-in Class Rep
                    rep_signature = st.session_state.get("active_rep_name", "Class Rep")
                    current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # ✅ AUTOMATIC SIGNATURE INJECTION
                    # Combines original text with a clean, uncrowded author signature trail
                    signed_announcement = (
                        f"{announcement_text.strip()}\n\n"
                        f"✍️ — Posted by: {rep_signature} ({current_time_str})"
                    )
                    
                    # Push the securely signed message to the cloud
                    success = db.post_announcement(signed_announcement)
                    if success:
                        st.success(f"🎉 Announcement successfully broadcasted under your name, {rep_signature}!")
                        st.rerun()
                    else:
                        st.error("⚠️ Failed to post announcement.")
            else:
                st.warning("Please enter some text before posting.")

        st.markdown("---")
        
        # Live Broadcast History Audit Panel Feed 
        st.markdown("##### 📚 Currently Broadcasted Announcements Archive")
        live_announcements = db.fetch_announcements()
        
        if live_announcements:
            st.write("Below are the active notifications currently displayed inside student account logs:")
            for idx, ann_dict in enumerate(live_announcements):
                time_stamp = ann_dict.get("timestamp", "N/A")
                message_content = ann_dict.get("text", "")
                
                # Visual notification card displays who authored the post automatically
                st.info(f"**Post #{len(live_announcements) - idx}** 📅 *Cloud Logged: {time_stamp}*\n\n{message_content}")
        else:
            st.caption("No historical announcement records found inside your cloud spreadsheet database rows.")

    st.markdown("---")

    # =========================================================
    # SECTION 3: UPLOAD MATERIALS (PDF FILES)
    # =========================================================
    st.subheader("📂 Upload Course Materials (PDFs)")
    with st.form("upload_materials_form", clear_on_submit=True):
        uploaded_file = st.file_uploader("Choose a PDF file:", type=["pdf"])
        submit_file = st.form_submit_button("📤 Upload Material to Cloud")
        if submit_file:
            if uploaded_file is not None:
                with st.spinner(f"Uploading {uploaded_file.name}..."):
                    file_bytes = uploaded_file.getvalue()
                    success = db.upload_material(file_bytes, uploaded_file.name, "application/pdf")
                    if success:
                        st.success(f"🎉 {uploaded_file.name} uploaded successfully and is now available to students!")
                        st.caption(f"Uploaded at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        st.rerun()
                    else:
                        st.error("⚠️ Upload failed. Check deployment link or file size limits.")
            else:
                st.warning("Please select a PDF file first.")

    st.markdown("---")

    # =========================================================
    # SECTION 4: AI TEAM ALLOCATION (HIDDEN IN EXPANDER BUTTON)
    # =========================================================
    st.subheader("🤖 Project Squad Configuration")
    with st.expander("🤖 Open AI Team Allocation Panel", expanded=False):
        st.write("Configure parameters to let Gemini automatically distribute students into balanced project groups.")
        team_size = st.slider("Target Number of Students per Group:", 2, 6, 3)
        custom_rules = st.text_area("Custom Constraints (Optional):", placeholder="e.g., Mix BMEC and BPPE students evenly across groups...")

        if st.button("🚀 Run AI Allocation Engine"):
            with st.spinner("AI is evaluating course tracking sheets and processing distributions..."):
                ai_output = ai.generate_teams(df_profiles, team_size, custom_rules)
                if "error" in ai_output:
                    st.error(f"AI Matrix Fault: {ai_output['error']}")
                else:
                    sync_response = db.save_group_allocations(ai_output)
                    if sync_response.get("status") == "success":
                        st.success("🎉 AI Allocation complete! Teams written securely to Google Sheet.")
                        st.caption(f"Allocation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        st.rerun()
                    else:
                        st.error("AI sorted successfully, but cloud transmission failed.")

    st.markdown("---")

    # =========================================================
    # SECTION 5: TEAM ROSTERS VIEW (ZOOMABLE INDIVIDUAL DATAFRAMES)
    # =========================================================
    st.subheader("👥 Finalized Project Squads")
    if st.button("📂 Show Allocated Groups"):
        assigned_students = db.fetch_roster()   
        assigned_students = assigned_students[assigned_students["Assigned Group"] != "Unassigned"]

        if assigned_students.empty:
            st.info("💡 No teams have been generated yet. Use the Allocation Engine drawer above.")
        else:
            for group in sorted(assigned_students["Assigned Group"].unique()):
                with st.container():
                    st.markdown(f"### 👥 {group}")
                    group_members = assigned_students[assigned_students["Assigned Group"] == group]
                    group_members = group_members.reset_index(drop=True)
                    group_members.index = group_members.index + 1
                    
                    # Zoomable dynamic dataframe table integration 
                    st.dataframe(
                        group_members[["Student Name", "Course Code", "Contact"]], 
                        use_container_width=True
                    )

                    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                    # CSV Individual Group Export
                    csv_group_data = group_members.to_csv(index=True).encode("utf-8")
                    st.download_button(f"⬇️ Download {group} (CSV)", data=csv_group_data, file_name=f"{group}_members.csv", mime="text/csv")

                    # In-Memory Excel Generation for Individual Groups [1.1]
                    group_buffer = io.BytesIO()
                    with pd.ExcelWriter(group_buffer, engine='openpyxl') as writer:
                        group_members.to_excel(writer, index=True, sheet_name=str(group)[:30]) 
                    
                    st.download_button(
                        label=f"⬇️ Download {group} (Excel)",
                        data=group_buffer.getvalue(),
                        file_name=f"{group}_members.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.markdown("<br>", unsafe_allow_html=True)

    # =========================================================
    # SECTION 6: STUDENT FEEDBACK INBOX MANAGER (HIDDEN)
    # =========================================================
    st.markdown("---")
    st.subheader("📬 Student Feedback Inbox")
    with st.expander("📬 Open Student Messages Inbox Panel", expanded=False):
        st.write("Review incoming inquiries, change requests, or private issues submitted by registered students:")
        
        feedback_logs = db.fetch_feedback()
        if feedback_logs:
            for idx, fb in enumerate(feedback_logs):
                # Verify column limits match array unpacking lengths safely
                if isinstance(fb, list) and len(fb) >= 5:
                    msg_time = fb[0]
                    msg_reg = fb[1]
                    msg_name = fb[2]
                    msg_status = fb[3]
                    msg_text = fb[4]
                    
                    # Renders a neat messaging layout card feed
                    st.warning(f"**From: {msg_name}** ({msg_reg}) ⏱️ *Sent: {msg_time}*\n\n**Message:** {msg_text}")
                    st.markdown("---")
        else:
            st.info("No incoming student messages found inside your cloud spreadsheet database rows.")

