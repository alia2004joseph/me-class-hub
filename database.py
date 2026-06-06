import pandas as pd
import requests
import base64
from cache import (
    cached_fetch_roster,
    cached_fetch_announcements,
    cached_fetch_materials,
    cached_fetch_feedback,
    cached_fetch_read_receipts,
    cached_fetch_file,
    cached_fetch_rep_replies,
    WEBHOOK_URL,
    EMPTY_COLUMNS,
)


class SheetDatabaseManager:
    """Handles REST API operations with Google Sheets Webhooks + Drive uploads."""

    def __init__(self):
        self.webhook_url = WEBHOOK_URL

    # ── Roster ───────────────────────────────────────────────
    def fetch_roster(self) -> pd.DataFrame:
        return cached_fetch_roster()

    def _get_empty_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(columns=EMPTY_COLUMNS)

    # ── Registration + deletion ──────────────────────────────
    def register_student(self, name: str, reg: str, code: str, contact: str) -> bool:
        name_parts = name.strip().split()
        if len(name_parts) >= 2:
            first_name  = name_parts[0].upper()
            other_names = [p.title() for p in name_parts[1:]]
            clean_name  = f"{first_name} {' '.join(other_names)}"
        elif len(name_parts) == 1:
            clean_name = name_parts[0].upper()
        else:
            clean_name = "Unknown"

        payload = {
            "action":         "register",
            "student_name":   clean_name,
            "reg_number":     reg.strip().upper(),
            "course_code":    code.strip().upper() if code else "UNASSIGNED",
            "contact":        contact.strip(),
            "assigned_group": "Unassigned"
        }
        try:
            ok = requests.post(self.webhook_url, json=payload, timeout=15).status_code == 200
            if ok:
                cached_fetch_roster.clear()
            return ok
        except:
            return False

    def delete_student(self, name: str) -> dict:
        payload = {"action": "delete", "student_name": name.strip()}
        try:
            result = requests.post(self.webhook_url, json=payload, timeout=15).json()
            cached_fetch_roster.clear()
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Group allocations ────────────────────────────────────
    def save_group_allocations(self, allocations_dict: dict) -> dict:
        payload = {"action": "updateGroups", "allocations": allocations_dict}
        try:
            result = requests.post(self.webhook_url, json=payload, timeout=15).json()
            cached_fetch_roster.clear()
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Announcements ────────────────────────────────────────
    def fetch_announcements(self) -> list:
        return cached_fetch_announcements()

    def post_announcement(self, text: str, priority: str = "Normal") -> bool:
        payload = {"action": "postAnnouncement", "text": text.strip(), "priority": priority}
        try:
            ok = requests.post(self.webhook_url, json=payload, timeout=15).status_code == 200
            if ok:
                cached_fetch_announcements.clear()
            return ok
        except:
            return False

    def delete_announcement(self, text: str) -> bool:
        payload = {"action": "deleteAnnouncement", "text": text.strip()}
        try:
            ok = requests.post(self.webhook_url, json=payload, timeout=15).status_code == 200
            if ok:
                cached_fetch_announcements.clear()
            return ok
        except:
            return False

    # ── Read receipts ────────────────────────────────────────
    def log_read_receipt(self, ann_id: str, student_name: str, reg_number: str) -> bool:
        payload = {
            "action":       "logReadReceipt",
            "ann_id":       ann_id,
            "student_name": student_name,
            "reg_number":   reg_number
        }
        try:
            return requests.post(self.webhook_url, json=payload, timeout=15).status_code == 200
        except:
            return False

    def fetch_read_receipts(self) -> list:
        return cached_fetch_read_receipts()

    # ── Materials ────────────────────────────────────────────
    def fetch_materials(self) -> list:
        return cached_fetch_materials()

    def fetch_file_bytes(self, url: str) -> bytes:
        return cached_fetch_file(url)

    def upload_material(self, file_bytes, file_name: str, mime_type: str) -> bool:
        try:
            encoded = base64.b64encode(file_bytes).decode("utf-8")
            payload = {
                "action":    "upload_material",
                "file_name": file_name,
                "mime_type": mime_type,
                "file_data": encoded
            }
            r = requests.post(self.webhook_url, json=payload, timeout=60)
            if r.status_code == 200:
                ok = r.json().get("status") == "success"
                if ok:
                    cached_fetch_materials.clear()
                return ok
            return False
        except Exception as e:
            print("Upload error:", e)
            return False

    def delete_material(self, file_name: str) -> bool:
        """Delete a material by file name from the Materials sheet."""
        payload = {
            "action":    "deleteMaterial",
            "file_name": file_name
        }
        try:
            ok = requests.post(self.webhook_url, json=payload, timeout=15).status_code == 200
            if ok:
                cached_fetch_materials.clear()
            return ok
        except:
            return False

    # ── Feedback ─────────────────────────────────────────────
    def submit_feedback(self, reg_num: str, name: str, message: str) -> bool:
        payload = {
            "action":       "postFeedback",
            "reg_number":   reg_num,
            "student_name": name,
            "message":      message.strip()
        }
        try:
            return requests.post(self.webhook_url, json=payload, timeout=15).status_code == 200
        except:
            return False

    def fetch_feedback(self) -> list:
        return cached_fetch_feedback()

    def delete_feedback(self, timestamp: str, reg_number: str) -> bool:
        """Delete a single feedback message by timestamp + reg_number."""
        payload = {
            "action":     "deleteFeedback",
            "timestamp":  timestamp,
            "reg_number": reg_number
        }
        try:
            ok = requests.post(self.webhook_url, json=payload, timeout=15).status_code == 200
            if ok:
                cached_fetch_feedback.clear()
            return ok
        except:
            return False

    def delete_all_feedback(self, reg_number: str) -> bool:
        """Delete all feedback messages for a specific student."""
        payload = {
            "action":     "deleteAllFeedback",
            "reg_number": reg_number
        }
        try:
            ok = requests.post(self.webhook_url, json=payload, timeout=15).status_code == 200
            if ok:
                cached_fetch_feedback.clear()
            return ok
        except:
            return False

    def update_feedback_status(self, timestamp: str, reg_number: str, status: str = "Reviewed") -> bool:
        """Update the status of a feedback message."""
        payload = {
            "action":     "updateFeedbackStatus",
            "timestamp":  timestamp,
            "reg_number": reg_number,
            "status":     status
        }
        try:
            ok = requests.post(self.webhook_url, json=payload, timeout=15).status_code == 200
            if ok:
                cached_fetch_feedback.clear()
            return ok
        except:
            return False

    # ── Rep Replies ──────────────────────────────────────────
    def post_rep_reply(self, reg_number: str, student_name: str, message: str, rep_name: str) -> bool:
        """
        Send a reply from the class rep to a specific student.
        Stored in the RepReplies sheet.
        """
        payload = {
            "action":       "postRepReply",
            "rep_name":     rep_name.strip(),
            "reg_number":   reg_number.strip().upper(),
            "student_name": student_name.strip(),
            "message":      message.strip()
        }
        try:
            ok = requests.post(self.webhook_url, json=payload, timeout=15).status_code == 200
            if ok:
                cached_fetch_rep_replies.clear()
            return ok
        except:
            return False

    def fetch_rep_replies(self, reg_number: str = None) -> list:
        """
        Fetch rep replies.
        Pass reg_number to get replies for a specific student (student inbox).
        Pass None to get all replies (rep overview).
        """
        return cached_fetch_rep_replies(reg_number=reg_number)

    def mark_rep_reply_read(self, timestamp: str, reg_number: str) -> bool:
        """Mark a rep reply as Read once the student has seen it."""
        payload = {
            "action":     "markRepReplyRead",
            "timestamp":  timestamp,
            "reg_number": reg_number.strip().upper()
        }
        try:
            ok = requests.post(self.webhook_url, json=payload, timeout=15).status_code == 200
            if ok:
                cached_fetch_rep_replies.clear()
            return ok
        except:
            return False
