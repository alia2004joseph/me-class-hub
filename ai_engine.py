"""
ai_engine.py — Multi-provider AI engine for Smart University App.

Features:
  1. Gemini multi-key rotation (quota safe)
  2. Fallback to Groq, Mistral, HuggingFace, Cloudflare
  3. PDF content cached 1 hour
  4. Per-student cooldown (30s)
  5. Strict academic system prompts
  6. AIStudyAssistant for students
  7. AIRepAssistant for Class Rep dashboard
  8. AISortingEngine for group allocation
"""

import time
import streamlit as st
import requests
import fitz  # PyMuPDF
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
    "You are a dedicated academic study assistant for university students. "
    "Your primary role is to help students understand their uploaded course materials. "
    "When a document is provided, base your answers STRICTLY on that document. "
    "For general academic questions (engineering, physics, mathematics, science), "
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

ADMIN_SYSTEM_PROMPT = (
    "You are an intelligent university administrative assistant helping a Super Admin "
    "manage multiple departments and year groups. "
    "Provide clear, structured, data-driven insights. "
    "Be concise and professional."
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
def _call_with_retry(model: str, contents: str, config) -> str:
    if _key_manager.has_keys():
        try:
            return try_gemini(model, contents, config)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                _key_manager.rotate()
            else:
                print(f"[Gemini error] {e}")

    groq_key = st.secrets.get("GROQ_API_KEY", "")
    if groq_key:
        try:
            return try_groq(contents, groq_key)
        except Exception as e:
            print(f"[Groq error] {e}")

    mistral_key = st.secrets.get("MISTRAL_API_KEY", "")
    if mistral_key:
        try:
            return try_mistral(contents, mistral_key)
        except Exception as e:
            print(f"[Mistral error] {e}")

    hf_token = st.secrets.get("HUGGINGFACE_TOKEN", "")
    if hf_token:
        try:
            return try_huggingface(contents, hf_token)
        except Exception as e:
            print(f"[HF error] {e}")

    cf_token   = st.secrets.get("CLOUDFLARE_TOKEN", "")
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
# AI SORTING ENGINE — Group Allocation
# ─────────────────────────────────────────────────────────────
class AISortingEngine:
    def generate_teams(
        self,
        df_profiles: pd.DataFrame,
        team_size: int,
        instructions: str
    ) -> dict:
        if not _key_manager.has_keys():
            return {"error": "No API keys found in secrets.toml."}
        try:
            clean_roster = df_profiles[
                ["Student Name", "Reg Number", "Course Code"]
            ].to_json(orient="records")

            prompt = (
                f"You are an academic project coordinator. Group the following student list into balanced teams "
                f"of approximately {team_size} members. Mix students from different course codes if possible.\n"
                f"Custom Constraints: {instructions}\n"
                f"Student Data Array: {clean_roster}\n\n"
                f"CRITICAL: Return a valid raw JSON object mapping every student's 'Reg Number' to their group name.\n"
                f"Example: {{\"25/U/0001/PS\": \"Team Alpha\", \"25/U/0002/PS\": \"Team Beta\"}}\n"
            )
            config = types.GenerateContentConfig(response_mime_type="application/json")
            result = _call_with_retry(ALLOC_MODEL, prompt, config)
            if result.startswith("⚠️"):
                return {"error": result}
            return json.loads(result)
        except Exception as e:
            return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# AI STUDY ASSISTANT — For Students
# ─────────────────────────────────────────────────────────────
class AIStudyAssistant:

    def _check_cooldown(self, student_reg: str) -> tuple[bool, int]:
        key       = f"ai_last_request_{student_reg}"
        last_time = st.session_state.get(key, 0)
        elapsed   = time.time() - last_time
        if elapsed < STUDENT_COOLDOWN_SECONDS:
            return False, int(STUDENT_COOLDOWN_SECONDS - elapsed)
        return True, 0

    def _record_request(self, student_reg: str):
        st.session_state[f"ai_last_request_{student_reg}"] = time.time()

    def summarize_material(
        self, pdf_text: str, file_name: str, student_reg: str = ""
    ) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if not pdf_text.strip():
            return "⚠️ Could not extract text from this PDF."
        if student_reg:
            ok, wait = self._check_cooldown(student_reg)
            if not ok:
                return f"⏳ Please wait {wait} seconds before making another request."
            self._record_request(student_reg)

        prompt = (
            f"Provide a COMPLETE and detailed summary of '{file_name}'.\n\n"
            f"## 📘 Summary of '{file_name}'\n\n"
            f"### 1. Main Topic\n"
            f"### 2. Key Concepts\n"
            f"### 3. Important Formulas & Definitions\n"
            f"### 4. Chapter/Section Breakdown\n"
            f"### 5. Study Tips\n\n"
            f"Document content:\n{pdf_text}"
        )
        config = types.GenerateContentConfig(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            temperature=0.3, max_output_tokens=3000)
        return _call_with_retry(STUDENT_MODEL, prompt, config)

    def ask_ai(
        self,
        question: str,
        chat_history: list,
        pdf_text: str = "",
        file_name: str = "",
        student_reg: str = ""
    ) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if student_reg:
            ok, wait = self._check_cooldown(student_reg)
            if not ok:
                return f"⏳ Please wait {wait} seconds."
            self._record_request(student_reg)

        context_block = ""
        if pdf_text.strip():
            context_block = (
                f"Selected material: '{file_name}'.\n"
                f"--- DOCUMENT START ---\n{pdf_text}\n--- DOCUMENT END ---\n\n"
            )
        history_block = ""
        if chat_history:
            for turn in chat_history[-6:]:
                role = "Student" if turn["role"] == "user" else "Assistant"
                history_block += f"{role}: {turn['content']}\n"
            history_block = f"Previous conversation:\n{history_block}\n"

        full_prompt = (
            f"{context_block}{history_block}"
            f"Student question: {question}\n\n"
            f"Provide a COMPLETE answer."
        )
        config = types.GenerateContentConfig(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            temperature=0.4, max_output_tokens=3000)
        return _call_with_retry(STUDENT_MODEL, full_prompt, config)

    def find_formula(
        self, topic: str, pdf_text: str, file_name: str, student_reg: str = ""
    ) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if student_reg:
            ok, wait = self._check_cooldown(student_reg)
            if not ok:
                return f"⏳ Please wait {wait} seconds."
            self._record_request(student_reg)

        prompt = (
            f"From '{file_name}', find ALL formulas related to: '{topic}'.\n"
            f"For each: write formula, define variables, explain usage, give example.\n\n"
            f"Document:\n{pdf_text}"
        )
        config = types.GenerateContentConfig(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            temperature=0.2, max_output_tokens=2000)
        return _call_with_retry(STUDENT_MODEL, prompt, config)

    def explain_concept(self, concept: str, student_reg: str = "") -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if student_reg:
            ok, wait = self._check_cooldown(student_reg)
            if not ok:
                return f"⏳ Please wait {wait} seconds."
            self._record_request(student_reg)

        prompt = (
            f"Explain this concept for a university student:\n\n"
            f"Concept: {concept}\n\n"
            f"1. Simple definition\n2. Detailed explanation\n"
            f"3. Key formulas\n4. Real-world example\n5. Common mistakes\n"
        )
        config = types.GenerateContentConfig(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            temperature=0.4, max_output_tokens=2000)
        return _call_with_retry(STUDENT_MODEL, prompt, config)


# ─────────────────────────────────────────────────────────────
# AI REP ASSISTANT — For Class Representative
# ─────────────────────────────────────────────────────────────
class AIRepAssistant:

    def draft_announcement(self, rough_idea: str, priority: str = "Normal") -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        prompt = (
            f"Help a Class Rep draft a professional announcement.\n"
            f"Priority: {priority}\nIdea: \"{rough_idea}\"\n\n"
            f"Write a complete, formal announcement ready to post. Return ONLY the text."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.5, max_output_tokens=1000)
        return _call_with_retry(REP_MODEL, prompt, config)

    def suggest_reply(self, student_name: str, student_message: str) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        prompt = (
            f"A Class Rep needs to reply to:\n"
            f"Student: {student_name}\nMessage: \"{student_message}\"\n\n"
            f"Write a professional, empathetic reply (3-5 sentences). Return ONLY the reply."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.5, max_output_tokens=500)
        return _call_with_retry(REP_MODEL, prompt, config)

    def summarize_feedback(self, feedback_list: list) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if not feedback_list:
            return "📭 No feedback messages to summarize."
        messages_text = ""
        for i, fb in enumerate(feedback_list[:20], 1):
            if isinstance(fb, list) and len(fb) >= 5:
                messages_text += f"{i}. [{fb[2]}]: {fb[4]}\n"
        prompt = (
            f"Analyze these student feedback messages and provide a structured summary.\n\n"
            f"Messages:\n{messages_text}\n\n"
            f"## 📊 Feedback Summary\n"
            f"### Common Issues\n### Urgent Matters\n### General Sentiment\n### Recommended Actions\n"
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.3, max_output_tokens=1500)
        return _call_with_retry(REP_MODEL, prompt, config)

    def format_timetable(self, raw_timetable: str) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        prompt = (
            f"Format this raw timetable into a clean, structured announcement.\n\n"
            f"Raw:\n{raw_timetable}\n\n"
            f"Format: Day | Time | Course | Venue. Easy to read on mobile. Return ready-to-post text."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.2, max_output_tokens=1500)
        return _call_with_retry(REP_MODEL, prompt, config)

    def check_timetable_conflicts(self, raw_timetable: str) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        prompt = (
            f"Check this timetable for: time clashes, venue conflicts, back-to-back classes, "
            f"unusual hours, missing info.\n\nTimetable:\n{raw_timetable}\n\n"
            f"## 🔍 Conflict Report\nList each issue. If none, confirm it looks clean."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.2, max_output_tokens=1000)
        return _call_with_retry(REP_MODEL, prompt, config)

    def answer_timetable_question(self, question: str, timetable_text: str) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        prompt = (
            f"Timetable:\n{timetable_text}\n\n"
            f"Student question: {question}\n\n"
            f"Answer directly from the timetable. If not found, say so politely."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.3, max_output_tokens=500)
        return _call_with_retry(REP_MODEL, prompt, config)


# ─────────────────────────────────────────────────────────────
# AI ADMIN ASSISTANT — For Super Admin
# ─────────────────────────────────────────────────────────────
class AIAdminAssistant:
    """AI assistant for the Super Admin dashboard."""

    def summarize_all_feedback(self, feedback_list: list, dept: str = "ALL") -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if not feedback_list:
            return "📭 No feedback to summarize."

        scope = f"department {dept}" if dept != "ALL" else "all departments"
        messages_text = ""
        for i, fb in enumerate(feedback_list[:30], 1):
            if isinstance(fb, list) and len(fb) >= 5:
                messages_text += f"{i}. [{fb[2]} | {fb[3] if len(fb)>5 else ''}]: {fb[4]}\n"

        prompt = (
            f"As a university admin, analyze feedback from {scope}.\n\n"
            f"Messages:\n{messages_text}\n\n"
            f"## 📊 University-Wide Feedback Analysis\n"
            f"### Top Issues Across Departments\n"
            f"### Departments Needing Attention\n"
            f"### Overall Student Sentiment\n"
            f"### Recommended Admin Actions\n"
        )
        config = types.GenerateContentConfig(
            system_instruction=ADMIN_SYSTEM_PROMPT,
            temperature=0.3, max_output_tokens=2000)
        return _call_with_retry(REP_MODEL, prompt, config)

    def generate_broadcast(self, rough_idea: str, priority: str = "Normal") -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        prompt = (
            f"Draft a university-wide broadcast announcement.\n"
            f"Priority: {priority}\nIdea: \"{rough_idea}\"\n\n"
            f"This will go to ALL departments and year groups. "
            f"Make it formal, clear, and appropriately scoped. Return ONLY the text."
        )
        config = types.GenerateContentConfig(
            system_instruction=ADMIN_SYSTEM_PROMPT,
            temperature=0.4, max_output_tokens=800)
        return _call_with_retry(REP_MODEL, prompt, config)

    def analyze_enrollment(self, df: pd.DataFrame) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if df.empty:
            return "No enrollment data available."

        # Normalise column names defensively before groupby
        df = df.copy()
        df.columns = [c.strip() for c in df.columns]
        col_map = {}
        for c in df.columns:
            if c.lower() in ("department", "dept", "dep"):
                col_map[c] = "Department"
            elif c.lower() in ("year", "year_group", "year of study"):
                col_map[c] = "Year"
        df = df.rename(columns=col_map)

        if "Department" not in df.columns:
            df["Department"] = "Unknown"
        if "Year" not in df.columns:
            df["Year"] = "Unknown"

        summary = df.groupby(["Department", "Year"]).size().reset_index(name="Count")
        summary_text = summary.to_string(index=False)

        prompt = (
            f"Analyze this university enrollment data and provide insights.\n\n"
            f"Enrollment by Department and Year:\n{summary_text}\n\n"
            f"Provide:\n"
            f"1. Which dept/year has the most students\n"
            f"2. Which has the least (may need attention)\n"
            f"3. Overall enrollment health\n"
            f"4. Any notable patterns\n"
            f"Keep it concise and actionable for an admin."
        )
        config = types.GenerateContentConfig(
            system_instruction=ADMIN_SYSTEM_PROMPT,
            temperature=0.3, max_output_tokens=800)
        return _call_with_retry(REP_MODEL, prompt, config)