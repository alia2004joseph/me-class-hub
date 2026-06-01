import streamlit as st
import pandas as pd
import requests
from google import genai
import json
from google.genai import types


# ==========================================
# 1. DATABASE MANAGER CLASS
# ==========================================
# ==========================================
# 1. DATABASE MANAGER CLASS (UPDATED)
# ==========================================
class SheetDatabaseManager:
    def __init__(self):
        self.webhook_url = st.secrets.get("sheet_webhook_url", "")
        self.csv_url = "https://google.com"

    def fetch_roster(self) -> pd.DataFrame:
        try:
            response = requests.get(self.webhook_url)
            if response.status_code == 200:
                data_json = response.json()
                if not data_json: return self._get_empty_dataframe()
                return pd.DataFrame(data_json)
            return self._get_empty_dataframe()
        except Exception as e:
            st.error(f"Database Connection Error: {e}")
            return self._get_empty_dataframe()

    def register_student(self, name: str, reg: str, code: str, contact: str) -> bool:
        payload = {"action": "register", "student_name": name.strip(), "reg_number": reg.strip(), "course_code": code, "contact": contact.strip(), "assigned_group": "Unassigned"}
        try: return requests.post(self.webhook_url, json=payload).status_code == 200
        except: return False

    def delete_student(self, name: str) -> dict:
        payload = {"action": "delete", "student_name": name.strip()}
        try: return requests.post(self.webhook_url, json=payload).json()
        except Exception as e: return {"status": "error", "message": str(e)}

    # --- NEW METHOD: SEND ALIGNED GROUPS BACK TO GOOGLE SHEETS ---
    def save_group_allocations(self, allocations_dict: dict) -> dict:
        """Sends group allocations payload to the Apps Script database."""
        payload = {
            "action": "updateGroups",
            "allocations": allocations_dict
        }
        try:
            response = requests.post(self.webhook_url, json=payload)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _get_empty_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(columns=["Timestamp", "Student Name", "Reg Number", "Course Code", "Contact", "Assigned Group"])


# ==========================================
# 2. AI ENGINE CLASS (UPDATED FOR JSON OUTPUT)
# ==========================================
class AISortingEngine:
    def __init__(self):
        self.api_key = st.secrets.get("GEMINI_API_KEY", "")

    def generate_teams(self, df_profiles: pd.DataFrame, team_size: int, instructions: str) -> dict:
        if not self.api_key:
            return {"error": "Missing API Key"}
        
        try:
            clean_roster = df_profiles[["Student Name", "Reg Number", "Course Code"]].to_json(orient="records")
            
            # We strictly enforce JSON structured output schema formatting from Gemini
            prompt = (
                f"You are an academic project coordinator. Group the following student list into balanced teams "
                f"of approximately {team_size} members. Mix students from different course codes if possible.\n"
                f"Custom Constraints: {instructions}\n"
                f"Student Data Array: {clean_roster}\n\n"
                f"CRITICAL: You must return the output as a valid raw JSON object. Do not include markdown blocks like ```json."
                f"The JSON object must map every student's 'Reg Number' to their newly assigned group name.\n"
                f"Example format:\n"
                f'{{"25/0001/PS": "Team Alpha", "25/0002/PS": "Team Beta"}}\n'
            )
            
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                # Forces response format validation
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            # Convert string response back to native python dictionary layout
            return json.loads(response.text)
        except Exception as e:
            return {"error": str(e)}


# ==========================================
# 3. DASHBOARD INTERFACE METHOD UPDATE
# ==========================================
# Paste this updated function inside your MechanicalEngineeringApp class
    def _render_class_rep_dashboard(self, df_profiles: pd.DataFrame):
        if st.session_state.role != "Class Rep":
            st.warning("🔒 Access Denied. Only Class Representatives can view student details and run the AI Sorting Engine.")
            return

        st.header("👑 Class Representative Control Center")
        st.markdown("---")
        
        st.subheader("📊 Private Student Roster")
        if df_profiles.empty or len(df_profiles) == 0:
            st.info("No students have filled in their details yet.")
            return
            
        st.dataframe(df_profiles, use_container_width=True)
        st.markdown("---")
        
        # --- DELETE RECORD FIELD ---
        st.subheader("🗑️ Delete Student Record")
        student_to_delete = st.text_input("Type the exact Full Name of the student to remove:", key="delete_name_input")
        if st.button("🗑️ Confirm Absolute Deletion"):
            if student_to_delete.strip():
                with st.spinner(f"Removing {student_to_delete}..."):
                    res = self.db.delete_student(student_to_delete)
                    if res.get("status") == "success":
                        st.success(f"✅ {student_to_delete} removed.")
                        st.session_state["delete_name_input"] = ""
                        st.rerun()
                    else:
                        st.error("Deletion failed.")
            else:
                st.warning("Please type a student's name first.")
                
        st.markdown("---")
        
               # --- AI TEAM ALLOCATION ENGINE PANEL ---
        st.subheader("🤖 AI Smart Team Allocation")
        team_size = st.slider("Target Number of Students per Team:", 2, 6, 3)
        rules = st.text_area("Custom Grouping Rules (Optional):", placeholder="e.g., Mix course codes evenly...")
        
        if st.button("🚀 Run AI Sorting Algorithm & Sync Cloud"):
            with st.spinner("AI is allocating groups and writing data to Google Sheets..."):
                ai_output = self.ai.generate_teams(df_profiles, team_size, rules)
                
                if "error" in ai_output:
                    st.error(f"AI Operation Failed: {ai_output['error']}")
                else:
                    # 1. Instantly display textual group assignments on the Streamlit dashboard
                    st.subheader("📋 New Team Assignments Preview")
                    
                    # Convert the raw data dictionary into a clean table structure for the user
                    preview_data = []
                    for reg_num, group_name in ai_output.items():
                        # Find the student's name corresponding to their registration ID
                        student_row = df_profiles[df_profiles["Reg Number"] == reg_num]
                        name = student_row["Student Name"].values[0] if not student_row.empty else "Unknown Student"
                        preview_data.append({"Reg Number": reg_num, "Student Name": name, "Assigned Team": group_name})
                    
                    st.dataframe(pd.DataFrame(preview_data), use_container_width=True)
                    
                    # 2. Push the group assignments back to your Google Sheet database
                    sync_response = self.db.save_group_allocations(ai_output)
                    
                    if sync_response.get("status") == "success":
                        st.success(f"🎉 Cloud Sync Successful! Updated {sync_response.get('updated')} rows inside your Google Sheet.")
                    else:
                        st.error(f"AI sorted successfully, but could not sync to cloud: {sync_response.get('message')}")


# ==========================================
# 3. INTERFACE BUILDER (MAIN APP CONTROL)
# ==========================================
class MechanicalEngineeringApp:
    """Assembles tabs, sidebars, and states using isolated system classes."""
    def __init__(self):
        st.set_page_config(page_title="ME Class Hub", page_icon="⚙️", layout="centered")
        self.db = SheetDatabaseManager()
        self.ai = AISortingEngine()

    def run(self):
        self._init_session_states()
        self._build_sidebar()
        
        st.title("⚙️ MECHANICAL ENGINEERING APP")
        
        tab1, tab2 = st.tabs(["📋 Student Profile Entry", "👑 Class Rep Dashboard"])
        
        # Load database records fresh into active application scope
        df_profiles = self.db.fetch_roster()
        
        with tab1:
            self._render_registration_form(df_profiles)
        with tab2:
            self._render_class_rep_dashboard(df_profiles)

    def _init_session_states(self):
        if "role" not in st.session_state:
            st.session_state.role = "Student"
        if "show_success_message" in st.session_state:
            st.success(f"🎉 Welcome aboard, {st.session_state['show_success_message']}! Profile created.")
            del st.session_state["show_success_message"]

    def _build_sidebar(self):
        st.sidebar.title("🔐 Access Control")
        selected_role = st.sidebar.radio("Identify your role:", ["Student", "Class Rep"])
        st.session_state.role = selected_role

    def _render_registration_form(self, df_profiles: pd.DataFrame):
        st.header("📝 Student Registration Form")
        st.write("Fill in your details below. Your entries will be processed privately by the Class Rep.")
        
        with st.form("student_registration_form", clear_on_submit=True):
            name = st.text_input("Full Name:", placeholder="e.g., John Doe")
            reg = st.text_input("Registration Number:", placeholder="e.g., 25/0000/PS")
            code = st.selectbox("Select Your Course Code:", options=["BMEC", "BPPE", "BAGE", "BWIE"], index=None, placeholder="Choose your program...")
            contact = st.text_input("Contact:")
            submit_btn = st.form_submit_button("Submit Profile")
            
            if submit_btn:
                if name and reg and code and contact:
                    # Check for duplicates cleanly in local dataframe
                    if "Reg Number" in df_profiles.columns and reg.strip() in df_profiles['Reg Number'].astype(str).values:
                        st.error(f"❌ Registration Number {reg} has already been registered!")
                    else:
                        with st.spinner("Saving details to Google Sheets..."):
                            if self.db.register_student(name, reg, code, contact):
                                st.session_state["show_success_message"] = name.strip()
                                st.rerun()
                            else:
                                st.error("⚠️ Connection error: Failed to reach Google server.")
                else:
                    st.error("⚠️ Please fill in all fields before submitting.")

    def _render_class_rep_dashboard(self, df_profiles: pd.DataFrame):
        if st.session_state.role != "Class Rep":
            st.warning("🔒 Access Denied. Only Class Representatives can view student details and run the AI Sorting Engine.")
            return

        st.header("👑 Class Representative Control Center")
        st.markdown("---")
        
        # Display Database Roster
        st.subheader("📊 Private Student Roster")
        if df_profiles.empty or len(df_profiles) == 0:
            st.info("No students have filled in their details yet.")
            return
            
        st.dataframe(df_profiles, use_container_width=True)
        st.markdown("---")
        
        # Isolated Manual Text Field Deletion Task
        st.subheader("🗑️ Delete Student Record")
        student_to_delete = st.text_input("Type the exact Full Name of the student to remove:")
        
        if st.button("🗑️ Confirm Absolute Deletion"):
            if student_to_delete.strip():
                with st.spinner(f"Removing {student_to_delete}..."):
                    res = self.db.delete_student(student_to_delete)
                    if res.get("status") == "success":
                        st.success(f"✅ {student_to_delete} has been removed successfully.")
                        st.session_state["delete_name_input"] = ""
                
                        st.rerun()
                    else:
                        st.error(f"Deletion failed: {res.get('message', 'Record not found')}")
            else:
                st.warning("Please type a student's name first.")
                
        st.markdown("---")
        
               # --- AI TEAM ALLOCATION ENGINE PANEL ---
        st.subheader("🤖 AI Smart Team Allocation")
        team_size = st.slider("Target Number of Students per Team:", 2, 6, 3)
        rules = st.text_area("Custom Grouping Rules (Optional):", placeholder="e.g., Mix course codes evenly...")
        
        # Make sure the name matches here
        if st.button("🚀 Run AI Sorting Algorithm & Sync Cloud"):
            with st.spinner("AI is allocating groups and writing data to Google Sheets..."):
                ai_output = self.ai.generate_teams(df_profiles, team_size, rules)
                
                if "error" in ai_output:
                    st.error(f"AI Operation Failed: {ai_output['error']}")
                else:
                    # 1. Transform raw data mapping into a readable table report
                    st.subheader("📋 New Team Assignments Preview")
                    preview_list = []
                    for reg_num, group_name in ai_output.items():
                        # Track student name corresponding to registration key
                        student_match = df_profiles[df_profiles["Reg Number"] == reg_num]
                        name = student_match["Student Name"].values[0] if not student_match.empty else "Unknown"
                        preview_list.append({"Reg Number": reg_num, "Student Name": name, "Assigned Team": group_name})
                    
                    # Output table onto Streamlit viewport page
                    st.dataframe(pd.DataFrame(preview_list), use_container_width=True)
                    
                    # 2. Sync allocations directly to Google Sheet
                    sync_response = self.db.save_group_allocations(ai_output)
                    
                    if sync_response.get("status") == "success":
                        st.success(f"🎉 Cloud Sync Successful! Updated rows inside your Google Sheet.")
                        st.rerun()
                    else:
                        st.error(f"AI sorted successfully, but cloud sync failed: {sync_response.get('message', 'Unknown Error')}")



# ==========================================
# APPLICATION ENTRY POINT Execution Execution
# ==========================================
if __name__ == "__main__":
    app = MechanicalEngineeringApp()
    app.run()
