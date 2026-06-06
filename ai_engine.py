"""
ai_assistant.py — Gemini-powered AI Study Assistant for MEC Student Portal.
Uses the same google.genai SDK pattern as AISortingEngine.
"""

import streamlit as st
import requests
import fitz  # PyMuPDF — pip install pymupdf
from google import genai
from google.genai import types


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

SYSTEM_INSTRUCTION = (
    "You are a knowledgeable and friendly academic study assistant "
    "for university students in the Mechanical Engineering department. "
    "You help students understand course materials, answer academic questions, "
    "explain concepts clearly, and summarize documents. "
    "When a document is provided, base your answers primarily on it. "
    "For general questions, use your full academic knowledge. "
    "Always be encouraging, clear, and concise."
)


@st.cache_data(ttl=3600, show_spinner=False)
def extract_pdf_text(url: str, file_name: str) -> str:
    """Download PDF from Google Drive and extract all text. Cached 1 hour."""
    try:
        if "drive.google.com" in url:
            if "/file/d/" in url:
                file_id = url.split("/file/d/")[1].split("/")[0]
                dl_url  = f"https://drive.google.com/uc?export=download&id={file_id}"
            else:
                dl_url = url
        else:
            dl_url = url

        response = requests.get(dl_url, timeout=30)
        if response.status_code != 200:
            return ""

        pdf_doc = fitz.open(stream=response.content, filetype="pdf")
        text    = ""
        for page in pdf_doc:
            text += page.get_text()
        pdf_doc.close()
        return text[:12000].strip()

    except Exception as e:
        print(f"[AIStudyAssistant] PDF extract error for {file_name}: {e}")
        return ""


class AIStudyAssistant:
    """Gemini-powered study assistant for MEC students."""

    def __init__(self):
        self.api_key = st.secrets.get("GEMINI_API_KEY", "")

    def _get_client(self):
        if not self.api_key:
            return None
        return genai.Client(api_key=self.api_key)

    def summarize_material(self, pdf_text: str, file_name: str) -> str:
        """Generate a structured summary of the selected material."""
        client = self._get_client()
        if not client:
            return "⚠️ GEMINI_API_KEY not found in secrets.toml."

        if not pdf_text.strip():
            return (
                "⚠️ Could not extract text from this PDF. "
                "It may be a scanned image or a protected file."
            )

        prompt = (
            f"Please summarize the following academic document titled '{file_name}'. "
            f"Structure your summary with:\n"
            f"1. **Main Topic** — what the document is about\n"
            f"2. **Key Concepts** — bullet points of the most important ideas\n"
            f"3. **Important Details** — any formulas, definitions, or facts to remember\n"
            f"4. **Study Tip** — one practical tip for understanding this material\n\n"
            f"Document content:\n{pdf_text}"
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.4,
                    max_output_tokens=1024,
                )
            )
            return response.text
        except Exception as e:
            return f"⚠️ Summary failed: {str(e)}"

    def ask_ai(
        self,
        question: str,
        chat_history: list,
        pdf_text: str = "",
        file_name: str = ""
    ) -> str:
        """
        Send a question to Gemini with optional PDF context and chat history.
        chat_history: list of {"role": "user"|"assistant", "content": str}
        """
        client = self._get_client()
        if not client:
            return "⚠️ GEMINI_API_KEY not found in secrets.toml."

        context_block = ""
        if pdf_text.strip():
            context_block = (
                f"The student has selected the following course material: '{file_name}'.\n"
                f"Use this as your primary reference when answering:\n\n"
                f"--- DOCUMENT START ---\n{pdf_text}\n--- DOCUMENT END ---\n\n"
            )

        history_block = ""
        if chat_history:
            for turn in chat_history[-6:]:
                role          = "Student" if turn["role"] == "user" else "Assistant"
                history_block += f"{role}: {turn['content']}\n"
            history_block = f"Previous conversation:\n{history_block}\n"

        full_prompt = (
            f"{context_block}"
            f"{history_block}"
            f"Student question: {question}"
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.4,
                    max_output_tokens=1024,
                )
            )
            return response.text
        except Exception as e:
            return f"⚠️ Error: {str(e)}"