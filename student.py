import streamlit as st
import requests
from database import SheetDatabaseManager


def render_student_interface(db: SheetDatabaseManager, df_profiles):
    st.title("📋 Student Portal")
    st.markdown("---")

    if "student_logged_in" not in st.session_state:
        st.session_state.student_logged_in = None
    if "show_reg_form" not in st.session_state:
        st.session_state.show_reg_form = False

    # ---------------------------
    # Login Section
    # ---------------------------
    if not st.session_state.student_logged_in and not st.session_state.show_reg_form:
        st.subheader("🔑 Student Account Login")
        login_reg = st.text_input(
            "Enter Your Registration Number:",
            placeholder="e.g., 25/U/0000/PS"
        ).strip().upper()

        col1, col2 = st.columns(2)
        with col1:
            login_btn = st.button("🔓 Log In")
        with col2:
            register_toggle_btn = st.button("📝 Register New Account")

        if register_toggle_btn:
            st.session_state.show_reg_form = True
            st.rerun()

        if login_btn:
            if not login_reg:
                st.warning("Please enter your Registration Number to log in.")
            elif not df_profiles.empty and login_reg in df_profiles['Reg Number'].astype(str).values:
                st.session_state.student_logged_in = login_reg
                st.session_state.show_reg_form = False
                st.rerun()
            else:
                st.error(f"❌ Account '{login_reg}' not found.")

    # ---------------------------
    # Registration Form
    # ---------------------------
    if st.session_state.show_reg_form:
        st.subheader("📝 Create New Student Account")
        with st.form("register_form", clear_on_submit=True):
            name = st.text_input("Full Name", placeholder="e.g., Obema Kelly")
            reg = st.text_input("Registration Number", placeholder="25/U/0000/PS").strip().upper()
            
            # ✅ Dropdown for Course Code
            code = st.selectbox(
                "Course Code",
                ["BMEC", "BBPE", "BWIE", "BAGE"],
                index=0
            )
            
            contact = st.text_input("Contact Info", placeholder="e.g., 074421539")
            submit_reg = st.form_submit_button("✅ Register")

            if submit_reg:
                if not name or not reg:
                    st.warning("Name and Registration Number are required.")
                else:
                    success = db.register_student(name, reg, code, contact)
                    if success:
                        st.session_state.show_success_message = name
                        st.session_state.show_reg_form = False
                        st.success(f"🎉 Account created for {name}. You can now log in.")
                        st.rerun()
                    else:
                        st.error("⚠️ Registration failed. Please try again.")

    # ---------------------------
    # Logged-in View
    # ---------------------------
    if st.session_state.student_logged_in:
        student_data = df_profiles[df_profiles["Reg Number"] == st.session_state.student_logged_in].iloc[0]
        st.success(f"👋 Welcome back, **{student_data['Student Name']}**!")

        st.markdown("---")
        # Announcements
        announcements = db.fetch_announcements()
        with st.expander("🔔 Noticeboard", expanded=True):
            if announcements:
                latest = announcements[0]
                latest_text = latest['text'] if isinstance(latest, dict) else str(latest)
                st.info(f"**Latest Update:** {latest_text}")
                for old_ann in announcements[1:]:
                    old_text = old_ann['text'] if isinstance(old_ann, dict) else str(old_ann)
                    st.write(f"- {old_text}")
            else:
                st.info("No announcements yet.")

        st.markdown("---")

        # Materials
        st.subheader("📚 Distributed Course Materials")
        materials_list = db.fetch_materials()
        with st.expander("📂 Study Documents", expanded=True):
            if materials_list:
                for item in materials_list:
                    # Handle dicts or lists
                    if isinstance(item, dict):
                        file_name = item.get("name", "Unnamed File")
                        file_url = item.get("url", "#")
                    elif isinstance(item, list) and len(item) >= 2:
                        file_name, file_url = item[0], item[1]
                    else:
                        file_name, file_url = "Unnamed File", "#"

                    st.markdown(f"📄 **{file_name}**")
                    try:
                        file_data = requests.get(file_url).content
                        st.download_button(
                            label="⬇️ Download",
                            data=file_data,
                            file_name=file_name,
                            mime="application/pdf"
                        )
                    except:
                        st.warning("⚠️ Unable to fetch file for download.")
            else:
                st.info("No study resource documents have been distributed yet.")

        st.markdown("---")

        # Group Allocation
        st.subheader("👥 Project Allocation")
        if st.button("🔎 Show My Group Members"):
            team_status = student_data["Assigned Group"]
            st.info(f"Your assigned project group is: **{team_status}**")

            group_members = df_profiles[df_profiles["Assigned Group"] == team_status]
            if not group_members.empty:
                st.table(group_members[["Student Name", "Course Code", "Contact"]].reset_index(drop=True))
            else:
                st.warning("No members found in your group yet.")

        st.markdown("---")
                # --- STUDENT PRIVATE FEEDBACK PANEL ---
        st.markdown("---")
        st.subheader("📬 Send Private Message to Class Rep")
        st.write("Have an issue with your team allocation, an error in your program code, or a confidential question? Message the reps privately here:")
        
        with st.form("student_feedback_form", clear_on_submit=True):
            user_msg = st.text_area("Type your message here:", placeholder="e.g., Hello Rep, I have an issue working with my assigned group members due to a schedule clash...", key="st_fb_area")
            submit_fb = st.form_submit_button("✉️ Send Private Message")
            
            if submit_fb:
                if user_msg.strip():
                    # Extract current student data safely from your active profile loop variables
                    s_name = student_data["Student Name"]
                    s_reg = st.session_state.student_logged_in
                    
                    with st.spinner("Delivering message safely..."):
                        if db.submit_feedback(s_reg, s_name, user_msg):
                            st.success("🚀 Message delivered safely! Your Class Representatives can now view this in their private inbox.")
                        else:
                            st.error("Submission failed. Connection error.")
                else:
                    st.warning("Please type a message before sending.")


        # Log Out
        if st.button("🔒 Log Out"):
            st.session_state.student_logged_in = None
            st.success("You have logged out successfully.")
            st.rerun()
