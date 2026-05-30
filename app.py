import streamlit as st
import pandas as pd
import os
import json
from google import genai
from google.genai import types

st.set_page_config(page_title="ME Class Hub", page_icon="⚙️", layout="centered")

# --- 1. ACCESS CONTROL ---
if "role" not in st.session_state:
    st.session_state.role = "Student"

st.sidebar.title("🔐 Access Control")
selected_role = st.sidebar.radio("Identify your role:", ["Student", "Class Rep"])
st.session_state.role = selected_role

# --- 2. DATA CONSTANTS & HANDLING ---
DATA_FILE = "student_profiles.csv"

def load_profiles():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["Student Name", "Reg Number", "Core Engineering Skills", "Assigned Group"])

# Load data into memory
df_profiles = load_profiles()

st.title("⚙️ ME Smart Team Allocation Portal")

# Create clean navigation tabs within the interface
tab1, tab2 = st.tabs(["📋 Student Profile Entry", "👑 Class Rep Dashboard"])

# ==========================================
# TAB 1: STUDENT PROFILE ENTRY (Open to All)
# ==========================================
with tab1:
    st.header("📝 Register Your Skills & Details")
    st.write("Fill in your details below. Your entries will be processed privately by the Class Rep to build project teams.")
    
    with st.form("student_registration_form", clear_on_submit=True):
        st_name = st.text_input("Full Name:", placeholder="e.g., John Doe")
        st_reg = st.text_input("Registration Number:", placeholder="e.g., ME/015/26")
        st_skills = st.text_area(
            "What are your core engineering skills / project preferences?", 
            placeholder="e.g., Strong at SolidWorks/CAD design, comfortable with MATLAB coding, prefer thermodynamic analysis, or good at technical report writing."
        )
        
        submit_reg = st.form_submit_button("Submit Profile")
        
        if submit_reg:
            if st_name and st_reg and st_skills:
                # Basic duplicate verification checking against registration numbers
                if st_reg.strip() in df_profiles['Reg Number'].astype(str).values:
                    st.error(f"❌ A profile with Registration Number {st_reg} has already been registered!")
                else:
                    new_student = pd.DataFrame([{
                        "Student Name": st_name.strip(),
                        "Reg Number": st_reg.strip(),
                        "Core Engineering Skills": st_skills.strip(),
                        "Assigned Group": "Unassigned"  # Starts off unassigned until AI sorts them
                    }])
                    
                    updated_df = pd.concat([df_profiles, new_student], ignore_index=True)
                    updated_df.to_csv(DATA_FILE, index=False)
                    st.success(f"🎉 Thank you {st_name}! Your details have been submitted securely.")
                    st.rerun()
            else:
                st.error("⚠️ Please fill in all fields before submitting.")

# ==========================================
# TAB 2: CLASS REP DASHBOARD (Private Panel)
# ==========================================
with tab2:
    if st.session_state.role != "Class Rep":
        st.warning("🔒 Access Denied. Only Class Representatives can view student details and run the AI Sorting Engine.")
    else:
        st.header("👑 Class Representative Control Center")
        st.write("Welcome! Below is the private database and the automated AI group configuration panel.")
        st.markdown("---")
        
        st.subheader("📊 Private Student Roster")
        if df_profiles.empty:
            st.info("No students have filled in their details yet.")
        else:
            # Display current registry to Class Rep only
            st.dataframe(df_profiles, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🤖 AI Smart Team Allocation")
            st.write("Let the AI analyze student skill summaries to form perfectly balanced engineering groups automatically.")
            
            # Rep configurations for team rules
            students_per_team = st.slider("Target Number of Students per Team:", 2, 6, 3)
            custom_instructions = st.text_area(
                "Custom Grouping Rules (Optional):",
                placeholder="e.g., Make sure every single team has at least one person who knows CAD/SolidWorks, and shuffle mixed skill sets evenly."
            )
            
            # --- AI EXECUTION ENGINE BUTTON ---
            if st.button("🚀 Run AI Sorting Algorithm"):
                # Safety check: Verify the secrets file exists before processing
                if "GEMINI_API_KEY" not in st.secrets:
                    st.error("⚠️ Configuration Error: 'GEMINI_API_KEY' was not found in your hidden .streamlit/secrets.toml file!")
                else:
                    with st.spinner("AI is analyzing student skills and engineering balanced teams..."):
                        try:
                            # Initializes client by retrieving string securely from hidden configurations
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            
                            # Convert current dataframe profiles into a compact JSON string for the AI to read
                            roster_json = df_profiles[["Student Name", "Reg Number", "Core Engineering Skills"]].to_json(orient="records")
                            
                            sorting_prompt = (
                                f"You are an academic project coordinator. Group the following student list into balanced teams "
                                f"of approximately {students_per_team} members based on their 'Core Engineering Skills'. "
                                f"Special instruction rules: {custom_instructions}\n\n"
                                f"Student Data Profiles:\n{roster_json}"
                            )
                            
                            # Force structured schema layout response
                            response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=sorting_prompt,
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json",
                                    response_schema=types.Schema(
                                        type=types.Type.OBJECT,
                                        properties={
                                            "teams": types.Schema(
                                                type=types.Type.ARRAY,
                                                items=types.Schema(
                                                    type=types.Type.OBJECT,
                                                    properties={
                                                        "team_name": types.Schema(type=types.Type.STRING),
                                                        "rationale": types.Schema(type=types.Type.STRING),
                                                        "members": types.Schema(
                                                            type=types.Type.ARRAY,
                                                            items=types.Schema(type=types.Type.STRING)
                                                        )
                                                    },
                                                    required=["team_name", "rationale", "members"]
                                                )
                                            )
                                        },
                                        required=["teams"]
                                    )
                                )
                            )
                            
                            ai_output = json.loads(response.text)
                            st.balloons()
                            st.success("🎉 AI sorting processing completed successfully!")
                            
                            # Display the configured teams on screen beautifully
                            for team in ai_output["teams"]:
                                with st.container(border=True):
                                    st.subheader(f"👥 {team['team_name']}")
                                    st.caption(f"💡 *Team Balance Rationale:* {team['rationale']}")
                                    
                                    # List out sorted names cleanly
                                    for member in team["members"]:
                                        st.write(f"🔹 {member}")
                                        
                                        # Update our dataframe in memory dynamically matching back via names
                                        df_profiles.loc[df_profiles['Student Name'] == member, 'Assigned Group'] = team['team_name']
                            
                            # Save back the results into our persistent local storage
                            df_profiles.to_csv(DATA_FILE, index=False)
                            st.toast("Updated student assignments committed safely to disk data storage!")
                            
                        except Exception as e:
                            st.error(f"Allocation Algorithm Fault: {e}")
