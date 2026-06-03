import streamlit as st
import pandas as pd
import json
from google import genai
from google.genai import types

class AISortingEngine:
    """Manages the engineering group allocation logic using Gemini."""
    def __init__(self):
        self.api_key = st.secrets.get("GEMINI_API_KEY", "")

    def generate_teams(self, df_profiles: pd.DataFrame, team_size: int, instructions: str) -> dict:
        if not self.api_key:
            return {"error": "Missing API Key"}
        
        try:
            clean_roster = df_profiles[["Student Name", "Reg Number", "Course Code"]].to_json(orient="records")
            
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
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception as e:
            return {"error": str(e)}
