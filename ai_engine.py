"""
ai_engine.py — Multi-provider AI engine for MEC Student Portal.

Features:
  1. Gemini multi-key rotation (quota safe)
  2. Fallback to Groq, Mistral, HuggingFace, Cloudflare
  3. PDF content cached 1 hour
  4. Per-student cooldown (30s)
  5. Strict academic system prompts
  6. AIStudyAssistant for students
  7. AIRepAssistant for Class Rep dashboard
"""

import time
import streamlit as st
import requests
import fitz  # PyMuPDF — pip install pymupdf
import pandas as pd
import json
from google import genai
from google.genai import types

# ─────────────────────────────────────────────
# MODEL CONFIGURATION
# ─────────────────────────────────────────────
STUDENT_MODEL            = "models/gemini-2.5-flash"
REP_MODEL                = "models/gemini-2.5-flash"
ALLOC_MODEL              = "models/gemini-2.5-flash"
STUDENT_COOLDOWN_SECONDS = 30

# ─────────────────────────────────────────────
# SYSTEM PROMPTS
# ─────────────────────────────────────────────
STUDENT_SYSTEM_PROMPT = (
    "You are a dedicated academic study assistant for university students "
    "in the Mechanical Engineering department. "
    "Your primary role is to help students understand their uploaded course materials. "
    "When a document is provided, base your answers STRICTLY on that document. "
    "For general academic questions (engineering, physics, mathematics), "
    "use your full academic knowledge but keep answers focused on university-level study. "
    "Do NOT answer questions about sports, entertainment, current events, or non-academic topics. "
    "Always give COMPLETE, detailed answers. Use clear structure."
)

REP_SYSTEM_PROMPT = (
    "You are a professional academic administrative assistant for a university Class Representative. "
    "You help the Class Rep manage their duties efficiently: drafting announcements, suggesting replies, "
    "summarizing feedback, formatting timetables, and checking conflicts. "
    "Always be professional, clear, and concise."
)

# ─────────────────────────────────────────────
# GEMINI KEY ROTATION MANAGER
# ─────────────────────────────────────────────
class KeyRotationManager:
    def __init__(self):
        self.keys = self._load_keys()
        self.current_index = 0

    def _load_keys(self) -> list:
        keys = []
        for i in range(1, 10):
            key = st.secrets.get(f"GEMINI_KEY_{i}", "")
            if key:
                keys.append(key)
        if not keys:
            old_key = st.secrets.get("GEMINI_API_KEY", "")
            if old_key:
                keys.append(old_key)
        return keys

    def get_client(self):
        if not self.keys:
            return None
        return genai.Client(api_key=self.keys[self.current_index])

    def rotate(self):
        if self.keys:
            self.current_index = (self.current_index + 1) % len(self.keys)

    def total_keys(self) -> int:
        return len(self.keys)

    def has_keys(self) -> bool:
        return len(self.keys) > 0

_key_manager = KeyRotationManager()

# ─────────────────────────────────────────────
# PROVIDER HELPERS
# ─────────────────────────────────────────────
def try_gemini(model, contents, config):
    client = _key_manager.get_client()
    return client.models.generate_content(model=model, contents=contents, config=config).text

def try_groq(contents, api_key):
    resp = requests.post(
        "https://api.groq.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "mixtral-8x7b", "messages": [{"role": "user", "content": contents}]}
    )
    return resp.json()["choices"][0]["message"]["content"]

def try_mistral(contents, api_key):
    resp = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "mistral-medium", "messages": [{"role": "user", "content": contents}]}
    )
    return resp.json()["choices"][0]["message"]["content"]

def try_huggingface(contents, token):
    resp = requests.post(
        "https://api-inference.huggingface.co/models/bigscience/bloom",
        headers={"Authorization": f"Bearer {token}"},
        json={"inputs": contents}
    )
    return resp.json()[0]["generated_text"]

def try_cloudflare(contents, token, account_id):
    resp = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-2-7b-chat-int8",
        headers={"Authorization": f"Bearer {token}"},
        json={"messages": [{"role": "user", "content": contents}]}
    )
    return resp.json()["result"]["response"]

# ─────────────────────────────────────────────
# FALLBACK MANAGER
# ─────────────────────────────────────────────
def _call_with_retry(model: str, contents: str, config, max_retries: int = None) -> str:
    # 1. Gemini
    if _key_manager.has_keys():
        try:
            return try_gemini(model, contents, config)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                _key_manager.rotate()
            else:
                print(f"[Gemini error] {e}")

    # 2. Groq
    groq_key = st.secrets.get("GROQ_API_KEY", "")
    if groq_key:
        try:
            return try_groq(contents, groq_key)
        except Exception as e:
            print(f"[Groq error] {e}")

    # 3. Mistral
    mistral_key = st.secrets.get("MISTRAL_API_KEY", "")
    if mistral_key:
        try:
            return try_mistral(contents, mistral_key)
        except Exception as e:
            print(f"[Mistral error] {e}")

    # 4. HuggingFace
    hf_token = st.secrets.get("HUGGINGFACE_TOKEN", "")
    if hf_token:
        try:
            return try_huggingface(contents, hf_token)
        except Exception as e:
            print(f"[HF error] {e}")

    # 5. Cloudflare
    cf_token = st.secrets.get("CLOUDFLARE_TOKEN", "")
    cf_account = st.secrets.get("CLOUDFLARE_ACCOUNT_ID", "")
    if cf_token and cf_account:
        try:
            return try_cloudflare(contents, cf_token, cf_account)
        except Exception as e:
            print(f"[Cloudflare error] {e}")

    return "⚠️ No AI provider available right now."

# ─────────────────────────────────────────────
# PDF TEXT EXTRACTION
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def extract_pdf_text(url: str, file_name: str) -> str:
    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            return ""
        pdf_doc = fitz.open(stream=response.content, filetype="pdf")
        text = "".join([page.get_text() for page in pdf_doc])
        pdf_doc.close()
        return text[:20000].strip()
    except Exception as e:
        print(f"[ai_engine] PDF extract error for {file_name}: {e}")
        return ""

# ─────────────────────────────────────────────────────────────
# AI SORTING ENGINE — Group Allocation for Class Rep
# ─────────────────────────────────────────────────────────────
class AISortingEngine:
    """Manages the engineering group allocation logic using Gemini."""

    def generate_teams(self, df_profiles: pd.DataFrame, team_size: int, instructions: str) -> dict:
        if not _key_manager.has_keys():
            return {"error": "No API keys found in secrets.toml."}

        try:
            clean_roster = df_profiles[["Student Name", "Reg Number", "Course Code"]].to_json(orient="records")

            prompt = (
                f"You are an academic project coordinator. Group the following student list into balanced teams "
                f"of approximately {team_size} members. Mix students from different course codes if possible.\n"
                f"Custom Constraints: {instructions}\n"
                f"Student Data Array: {clean_roster}\n\n"
                f"CRITICAL: You must return the output as a valid raw JSON object. "
                f"Do not include markdown blocks like ```json. "
                f"The JSON object must map every student's 'Reg Number' to their newly assigned group name.\n"
                f"Example format:\n"
                f'{{"25/U/0001/PS": "Team Alpha", "25/U/0002/PS": "Team Beta"}}\n'
            )

            config = types.GenerateContentConfig(
                response_mime_type="application/json"
            )

            result = _call_with_retry(ALLOC_MODEL, prompt, config)

            # If it returned an error string, pass it through
            if result.startswith("⚠️") or result.startswith("⏳"):
                return {"error": result}

            return json.loads(result)

        except Exception as e:
            return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# AI STUDY ASSISTANT — For Students
# ─────────────────────────────────────────────────────────────
class AIStudyAssistant:
    """
    Gemini-powered study assistant for MEC students.
    Features:
    - Summarize uploaded course materials
    - Answer questions strictly from selected PDF
    - General academic Q&A for engineering topics
    - Per-student cooldown to prevent quota exhaustion
    """

    def _check_cooldown(self, student_reg: str) -> tuple[bool, int]:
        key       = f"ai_last_request_{student_reg}"
        last_time = st.session_state.get(key, 0)
        elapsed   = time.time() - last_time
        if elapsed < STUDENT_COOLDOWN_SECONDS:
            remaining = int(STUDENT_COOLDOWN_SECONDS - elapsed)
            return False, remaining
        return True, 0

    def _record_request(self, student_reg: str):
        st.session_state[f"ai_last_request_{student_reg}"] = time.time()

    def summarize_material(self, pdf_text: str, file_name: str, student_reg: str = "") -> str:
        """Generate a complete structured summary of the selected material."""
        if not _key_manager.has_keys():
            return "⚠️ No API keys found in secrets.toml."

        if not pdf_text.strip():
            return (
                "⚠️ Could not extract text from this PDF. "
                "It may be a scanned image or a protected file."
            )

        if student_reg:
            can_proceed, remaining = self._check_cooldown(student_reg)
            if not can_proceed:
                return f"⏳ Please wait {remaining} seconds before making another request."
            self._record_request(student_reg)

        prompt = (
            f"Please provide a COMPLETE and detailed summary of the academic document titled '{file_name}'. "
            f"Do NOT cut off the summary — cover everything in the document.\n\n"
            f"Structure your summary exactly as follows:\n\n"
            f"## 📘 Summary of '{file_name}'\n\n"
            f"### 1. Main Topic\n"
            f"What is this document about? Give a clear overview.\n\n"
            f"### 2. Key Concepts\n"
            f"List ALL important concepts, theories, and principles covered.\n\n"
            f"### 3. Important Formulas & Definitions\n"
            f"List every formula, equation, or definition mentioned.\n\n"
            f"### 4. Chapter/Section Breakdown\n"
            f"Summarize each major section or topic in the document.\n\n"
            f"### 5. Study Tips\n"
            f"Give 2-3 practical tips for understanding and remembering this material.\n\n"
            f"Document content:\n{pdf_text}"
        )

        config = types.GenerateContentConfig(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=3000,
        )

        return _call_with_retry(STUDENT_MODEL, prompt, config)

    def ask_ai(
        self,
        question: str,
        chat_history: list,
        pdf_text: str = "",
        file_name: str = "",
        student_reg: str = ""
    ) -> str:
        """Answer a student question with optional PDF context and chat history."""
        if not _key_manager.has_keys():
            return "⚠️ No API keys found in secrets.toml."

        if student_reg:
            can_proceed, remaining = self._check_cooldown(student_reg)
            if not can_proceed:
                return f"⏳ Please wait {remaining} seconds before sending another question."
            self._record_request(student_reg)

        context_block = ""
        if pdf_text.strip():
            context_block = (
                f"The student has selected the following course material: '{file_name}'.\n"
                f"Base your answer PRIMARILY on this document:\n\n"
                f"--- DOCUMENT START ---\n{pdf_text}\n--- DOCUMENT END ---\n\n"
            )

        history_block = ""
        if chat_history:
            for turn in chat_history[-6:]:
                role           = "Student" if turn["role"] == "user" else "Assistant"
                history_block += f"{role}: {turn['content']}\n"
            history_block = f"Previous conversation:\n{history_block}\n"

        full_prompt = (
            f"{context_block}"
            f"{history_block}"
            f"Student question: {question}\n\n"
            f"Provide a COMPLETE answer. Do not cut off mid-response."
        )

        config = types.GenerateContentConfig(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=3000,
        )

        return _call_with_retry(STUDENT_MODEL, full_prompt, config)

    def find_formula(self, topic: str, pdf_text: str, file_name: str, student_reg: str = "") -> str:
        """Find and explain formulas related to a topic from the uploaded material."""
        if not _key_manager.has_keys():
            return "⚠️ No API keys found in secrets.toml."

        if student_reg:
            can_proceed, remaining = self._check_cooldown(student_reg)
            if not can_proceed:
                return f"⏳ Please wait {remaining} seconds before making another request."
            self._record_request(student_reg)

        prompt = (
            f"From the document '{file_name}', find ALL formulas and equations related to: '{topic}'.\n\n"
            f"For each formula found:\n"
            f"1. Write the formula clearly\n"
            f"2. Define every variable/symbol\n"
            f"3. Explain when and how to use it\n"
            f"4. Give a simple example if possible\n\n"
            f"If no formula is found in the document, say so clearly and explain the concept instead.\n\n"
            f"Document:\n{pdf_text}"
        )

        config = types.GenerateContentConfig(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=2000,
        )

        return _call_with_retry(STUDENT_MODEL, prompt, config)

    def explain_concept(self, concept: str, student_reg: str = "") -> str:
        """Explain an engineering concept clearly without needing a PDF."""
        if not _key_manager.has_keys():
            return "⚠️ No API keys found in secrets.toml."

        if student_reg:
            can_proceed, remaining = self._check_cooldown(student_reg)
            if not can_proceed:
                return f"⏳ Please wait {remaining} seconds before making another request."
            self._record_request(student_reg)

        prompt = (
            f"Explain the following engineering/academic concept clearly for a university student:\n\n"
            f"Concept: {concept}\n\n"
            f"Structure your explanation:\n"
            f"1. Simple definition (1-2 sentences)\n"
            f"2. Detailed explanation\n"
            f"3. Key formulas or principles involved\n"
            f"4. Real-world example or application\n"
            f"5. Common mistakes students make\n"
        )

        config = types.GenerateContentConfig(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=2000,
        )

        return _call_with_retry(STUDENT_MODEL, prompt, config)


# ─────────────────────────────────────────────────────────────
# AI REP ASSISTANT — For Class Representative
# ─────────────────────────────────────────────────────────────
class AIRepAssistant:
    """
    Gemini-powered assistant for the Class Representative.
    Features:
    - Draft professional announcements
    - Suggest replies to student messages
    - Summarize student feedback inbox
    - Format timetable data into clean announcements
    - Check timetable for conflicts/clashes
    """

    def draft_announcement(self, rough_idea: str, priority: str = "Normal") -> str:
        """Turn a rough idea into a professional class announcement."""
        if not _key_manager.has_keys():
            return "⚠️ No API keys found in secrets.toml."

        prompt = (
            f"You are helping a university Class Representative draft a professional announcement.\n\n"
            f"Priority level: {priority}\n"
            f"Rough idea from rep: \"{rough_idea}\"\n\n"
            f"Write a complete, professional class announcement that:\n"
            f"- Has a clear subject/heading\n"
            f"- Is formal but friendly in tone\n"
            f"- Includes all relevant details from the rough idea\n"
            f"- Is appropriate for a university student audience\n"
            f"- {'Uses urgent language and ALL CAPS for key info' if priority == 'Urgent' else 'Uses a calm, informative tone'}\n\n"
            f"Return ONLY the announcement text, ready to post."
        )

        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.5,
            max_output_tokens=1000,
        )

        return _call_with_retry(REP_MODEL, prompt, config)

    def suggest_reply(self, student_name: str, student_message: str) -> str:
        """Suggest a professional reply to a student's feedback message."""
        if not _key_manager.has_keys():
            return "⚠️ No API keys found in secrets.toml."

        prompt = (
            f"A university Class Representative needs to reply to this student message.\n\n"
            f"Student name: {student_name}\n"
            f"Student message: \"{student_message}\"\n\n"
            f"Write a professional, empathetic, and helpful reply that:\n"
            f"- Addresses the student by name\n"
            f"- Acknowledges their concern or question\n"
            f"- Provides a helpful response or next steps\n"
            f"- Is friendly but professional\n"
            f"- Is concise (3-5 sentences)\n\n"
            f"Return ONLY the reply text, ready to send."
        )

        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.5,
            max_output_tokens=500,
        )

        return _call_with_retry(REP_MODEL, prompt, config)

    def summarize_feedback(self, feedback_list: list) -> str:
        """Analyze all student feedback and give the rep a summary report."""
        if not _key_manager.has_keys():
            return "⚠️ No API keys found in secrets.toml."

        if not feedback_list:
            return "📭 No feedback messages to summarize."

        messages_text = ""
        for i, fb in enumerate(feedback_list[:20], 1):
            if isinstance(fb, list) and len(fb) >= 5:
                messages_text += f"{i}. [{fb[2]}]: {fb[4]}\n"

        prompt = (
            f"Analyze these student feedback messages sent to the Class Representative "
            f"and provide a structured summary report.\n\n"
            f"Messages:\n{messages_text}\n\n"
            f"Your report should include:\n"
            f"## 📊 Feedback Summary Report\n\n"
            f"### Common Issues\n"
            f"What are the most frequently raised problems or questions?\n\n"
            f"### Urgent Matters\n"
            f"Are there any messages that seem urgent or need immediate attention?\n\n"
            f"### General Sentiment\n"
            f"What is the overall mood/sentiment of students?\n\n"
            f"### Recommended Actions\n"
            f"What should the Class Rep prioritize responding to or acting on?\n"
        )

        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=1500,
        )

        return _call_with_retry(REP_MODEL, prompt, config)

    def format_timetable(self, raw_timetable: str) -> str:
        """Format raw timetable text into a clean structured announcement."""
        if not _key_manager.has_keys():
            return "⚠️ No API keys found in secrets.toml."

        prompt = (
            f"Format the following raw timetable information into a clean, "
            f"well-structured class timetable announcement.\n\n"
            f"Raw timetable info:\n{raw_timetable}\n\n"
            f"Format it as a proper timetable with:\n"
            f"- A clear heading\n"
            f"- Organized by day of the week\n"
            f"- Each entry showing: Day | Time | Course | Venue\n"
            f"- Easy to read on a phone screen\n"
            f"- A note at the bottom about any important reminders\n\n"
            f"Return the formatted timetable ready to post as an announcement."
        )

        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=1500,
        )

        return _call_with_retry(REP_MODEL, prompt, config)

    def check_timetable_conflicts(self, raw_timetable: str) -> str:
        """Check a timetable for scheduling conflicts, clashes, or issues."""
        if not _key_manager.has_keys():
            return "⚠️ No API keys found in secrets.toml."

        prompt = (
            f"Carefully analyze this class timetable for scheduling problems.\n\n"
            f"Timetable:\n{raw_timetable}\n\n"
            f"Check for:\n"
            f"1. Time clashes — two classes at the same time\n"
            f"2. Venue conflicts — same room booked twice at the same time\n"
            f"3. Back-to-back classes with no break\n"
            f"4. Unusual scheduling (e.g. classes at odd hours)\n"
            f"5. Missing information (courses with no venue or time)\n\n"
            f"## 🔍 Timetable Conflict Report\n\n"
            f"List each issue found clearly. If no conflicts found, confirm the timetable looks clean."
        )

        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=1000,
        )

        return _call_with_retry(REP_MODEL, prompt, config)

    def answer_timetable_question(self, question: str, timetable_text: str) -> str:
        """Answer a student question about the timetable."""
        if not _key_manager.has_keys():
            return "⚠️ No API keys found in secrets.toml."

        prompt = (
            f"A student is asking about the class timetable.\n\n"
            f"Timetable:\n{timetable_text}\n\n"
            f"Student question: {question}\n\n"
            f"Answer clearly and directly based strictly on the timetable above. "
            f"If the answer cannot be found in the timetable, say so politely."
        )

        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=500,
        )

        return _call_with_retry(REP_MODEL, prompt, config)