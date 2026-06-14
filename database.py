"""
database.py — REST API operations with Google Sheets Webhooks + Drive uploads.
Read receipts removed. Rep management via GAS added.
All methods scoped by department and year.
"""

import pandas as pd
import requests
import base64
from cache import (
    cached_fetch_roster,
    cached_fetch_announcements,
    cached_fetch_materials,
    cached_fetch_feedback,
    cached_fetch_file,
    cached_fetch_rep_replies,
    cached_fetch_reps,
    cached_fetch_timetable,
    WEBHOOK_URL,
    EMPTY_COLUMNS,
)


class SheetDatabaseManager:

    def __init__(self):
        self.webhook_url = WEBHOOK_URL

    # ── Roster ───────────────────────────────────────────────
    def fetch_roster(self, dept: str = "ALL", year: str = "ALL") -> pd.DataFrame:
        return cached_fetch_roster(dept=dept, year=year)

    def register_student(
        self, name: str, reg: str, code: str,
        contact: str, dept: str, year: str,pin: str = None
    ) -> bool:
        parts = name.strip().split()
        if len(parts) >= 2:
            clean = f"{parts[0].upper()} {' '.join(p.title() for p in parts[1:])}"
        elif len(parts) == 1:
            clean = parts[0].upper()
        else:
            clean = "Unknown"

        payload = {
            "action":         "register",
            "student_name":   clean,
            "reg_number":     reg.strip().upper(),
            "course_code":    code.strip().upper() if code else "UNASSIGNED",
            "contact":        contact.strip(),
            "assigned_group": "Unassigned",
            "department":     dept.strip().upper(),
            "year":           year.strip(),
            "pin":            pin
        }
        try:
            ok = requests.post(self.webhook_url, json=payload, timeout=15).status_code == 200
            if ok: cached_fetch_roster.clear()
            return ok
        except:
            return False

    def delete_student(self, name: str) -> dict:
        try:
            result = requests.post(
                self.webhook_url,
                json={"action": "delete", "student_name": name.strip()},
                timeout=15
            ).json()
            cached_fetch_roster.clear()
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def save_group_allocations(self, allocations_dict: dict) -> dict:
        try:
            result = requests.post(
                self.webhook_url,
                json={"action": "updateGroups", "allocations": allocations_dict},
                timeout=15
            ).json()
            cached_fetch_roster.clear()
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Announcements ────────────────────────────────────────
    def fetch_announcements(self, dept: str = "ALL", year: str = "ALL") -> list:
        return cached_fetch_announcements(dept=dept, year=year)

    def post_announcement(
        self, text: str, priority: str = "Normal",
        dept: str = "ALL", year: str = "ALL"
    ) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action": "postAnnouncement", "text": text.strip(),
                "priority": priority, "dept": dept, "year": year,
            }, timeout=15).status_code == 200
            if ok: cached_fetch_announcements.clear()
            return ok
        except:
            return False

    def delete_announcement(self, text: str) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action": "deleteAnnouncement", "text": text.strip()
            }, timeout=15).status_code == 200
            if ok: cached_fetch_announcements.clear()
            return ok
        except:
            return False

    def broadcast_announcement(self, text: str, priority: str = "Normal") -> bool:
        return self.post_announcement(text, priority, dept="ALL", year="ALL")

    # ── Materials ────────────────────────────────────────────
    def fetch_materials(self, dept: str = "ALL", year: str = "ALL") -> list:
        return cached_fetch_materials(dept=dept, year=year)

    def fetch_file_bytes(self, url: str) -> bytes:
        return cached_fetch_file(url)

    def upload_material(
        self, file_bytes, file_name: str, mime_type: str,
        dept: str = "ALL", year: str = "ALL"
    ) -> bool:
        try:
            encoded = base64.b64encode(file_bytes).decode("utf-8")
            r = requests.post(self.webhook_url, json={
                "action": "upload_material", "file_name": file_name,
                "mime_type": mime_type, "file_data": encoded,
                "dept": dept, "year": year,
            }, timeout=60)
            if r.status_code == 200:
                ok = r.json().get("status") == "success"
                if ok: cached_fetch_materials.clear()
                return ok
            return False
        except Exception as e:
            print("Upload error:", e)
            return False

    def delete_material(self, file_name: str) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action": "deleteMaterial", "file_name": file_name
            }, timeout=15).status_code == 200
            if ok: cached_fetch_materials.clear()
            return ok
        except:
            return False

    # ── Feedback ─────────────────────────────────────────────
    def fetch_feedback(self, dept: str = "ALL", year: str = "ALL") -> list:
        return cached_fetch_feedback(dept=dept, year=year)

    def submit_feedback(
        self, reg_num: str, name: str, message: str,
        dept: str = "ALL", year: str = "ALL"
    ) -> bool:
        try:
            return requests.post(self.webhook_url, json={
                "action": "postFeedback", "reg_number": reg_num,
                "student_name": name, "message": message.strip(),
                "dept": dept, "year": year,
            }, timeout=15).status_code == 200
        except:
            return False

    def delete_feedback(self, timestamp: str, reg_number: str) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action": "deleteFeedback",
                "timestamp": timestamp, "reg_number": reg_number
            }, timeout=15).status_code == 200
            if ok: cached_fetch_feedback.clear()
            return ok
        except:
            return False

    def delete_all_feedback(self, reg_number: str) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action": "deleteAllFeedback", "reg_number": reg_number
            }, timeout=15).status_code == 200
            if ok: cached_fetch_feedback.clear()
            return ok
        except:
            return False

    def update_feedback_status(
        self, timestamp: str, reg_number: str, status: str = "Reviewed"
    ) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action": "updateFeedbackStatus",
                "timestamp": timestamp, "reg_number": reg_number, "status": status
            }, timeout=15).status_code == 200
            if ok: cached_fetch_feedback.clear()
            return ok
        except:
            return False

    # ── Rep Replies ──────────────────────────────────────────
    def fetch_rep_replies(
        self, reg_number: str = None,
        dept: str = "ALL", year: str = "ALL"
    ) -> list:
        return cached_fetch_rep_replies(reg_number=reg_number, dept=dept, year=year)

    def post_rep_reply(
        self, reg_number: str, student_name: str,
        message: str, rep_name: str,
        dept: str = "ALL", year: str = "ALL"
    ) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action": "postRepReply",
                "rep_name": rep_name.strip(),
                "reg_number": reg_number.strip().upper(),
                "student_name": student_name.strip(),
                "message": message.strip(),
                "dept": dept, "year": year,
            }, timeout=15).status_code == 200
            if ok: cached_fetch_rep_replies.clear()
            return ok
        except:
            return False

    def mark_rep_reply_read(self, timestamp: str, reg_number: str) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action": "markRepReplyRead",
                "timestamp": timestamp,
                "reg_number": reg_number.strip().upper()
            }, timeout=15).status_code == 200
            if ok: cached_fetch_rep_replies.clear()
            return ok
        except:
            return False

    # ── Rep Account Management ───────────────────────────────
    def fetch_reps(self) -> list:
        return cached_fetch_reps()

    def verify_rep(self, dept: str, year: str, password: str) -> dict:
        """
        Verify rep credentials against the Reps Sheet via GAS.
        Returns dict with status + rep_name + rep_reg on success.
        """
        try:
            import urllib.parse
            url = (
                f"{self.webhook_url}"
                f"?action=verifyRep"
                f"&dept={urllib.parse.quote(dept)}"
                f"&year={urllib.parse.quote(year)}"
                f"&password={urllib.parse.quote(password)}"
            )
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                return r.json()
            return {"status": "error", "message": "Server error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def assign_rep(
        self, dept: str, year: str,
        rep_name: str, rep_reg: str, password: str
    ) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action":   "assignRep",
                "dept":     dept.strip().upper(),
                "year":     year.strip(),
                "rep_name": rep_name.strip(),
                "rep_reg":  rep_reg.strip().upper(),
                "password": password.strip(),
            }, timeout=15).status_code == 200
            if ok: cached_fetch_reps.clear()
            return ok
        except:
            return False

    def delete_rep(self, dept: str, year: str) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action": "deleteRep",
                "dept":   dept.strip().upper(),
                "year":   year.strip(),
            }, timeout=15).status_code == 200
            if ok: cached_fetch_reps.clear()
            return ok
        except:
            return False

    def change_rep_password(
        self, dept: str, year: str,
        old_password: str, new_password: str
    ) -> dict:
        try:
            r = requests.post(self.webhook_url, json={
                "action":       "changeRepPassword",
                "dept":         dept.strip().upper(),
                "year":         year.strip(),
                "old_password": old_password.strip(),
                "new_password": new_password.strip(),
            }, timeout=15)
            if r.status_code == 200:
                return r.json()
            return {"status": "error", "message": "Server error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Super Admin ──────────────────────────────────────────
    def fetch_all_roster(self) -> pd.DataFrame:
        return cached_fetch_roster(dept="ALL", year="ALL")

    def fetch_all_feedback(self) -> list:
        return cached_fetch_feedback(dept="ALL", year="ALL")

    def fetch_all_announcements(self) -> list:
        return cached_fetch_announcements(dept="ALL", year="ALL")


    # ── Department Management ─────────────────────────────────
    def fetch_departments(self) -> list:
        try:
            r = requests.get(f"{self.webhook_url}?action=getDepartments", timeout=10)
            if r.status_code == 200:
                return r.json()
            return []
        except:
            return []

    def add_department(
        self, code: str, name: str,
        color: str, light: str, courses: str
    ) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action":  "addDepartment",
                "code":    code.strip().upper(),
                "name":    name.strip(),
                "color":   color.strip(),
                "light":   light.strip(),
                "courses": courses.strip().upper(),
            }, timeout=15).status_code == 200
            if ok:
                from config import load_departments
                load_departments.clear()
            return ok
        except:
            return False

    def update_department(
        self, code: str, name: str,
        color: str, light: str, courses: str
    ) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action":  "updateDepartment",
                "code":    code.strip().upper(),
                "name":    name.strip(),
                "color":   color.strip(),
                "light":   light.strip(),
                "courses": courses.strip().upper(),
            }, timeout=15).status_code == 200
            if ok:
                from config import load_departments
                load_departments.clear()
            return ok
        except:
            return False

    def delete_department(self, code: str) -> dict:
        """
        Delete a department. GAS will block if students are registered.
        Returns {status, message, student_count}
        """
        try:
            r = requests.post(self.webhook_url, json={
                "action": "deleteDepartment",
                "code":   code.strip().upper(),
            }, timeout=15)
            if r.status_code == 200:
                result = r.json()
                if result.get("status") == "success":
                    from config import load_departments
                    load_departments.clear()
                return result
            return {"status": "error", "message": "Server error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_contact(self, reg_number: str, new_contact: str) -> bool:
        """Update a student's contact number in the Roster sheet."""
        try:
            ok = requests.post(self.webhook_url, json={
                "action":      "updateContact",
                "reg_number":  reg_number.strip().upper(),
                "new_contact": new_contact.strip(),
            }, timeout=15).status_code == 200
            if ok:
                cached_fetch_roster.clear()
            return ok
        except:
            return False

    # ── Student PIN Authentication ────────────────────────────
    def verify_student(self, reg_number: str, pin: str) -> dict:
        """
        Verify student login credentials.
        Returns {status, profile, pin_set} on success.
        pin_set=False means student has no PIN yet (first login).
        """
        try:
            r = requests.post(self.webhook_url, json={
                "action":     "verifyStudent",
                "reg_number": reg_number.strip().upper(),
                "pin":        pin.strip(),
            }, timeout=15)
            if r.status_code == 200:
                return r.json()
            return {"status": "error", "message": "Server error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def set_pin(self, reg_number: str, new_pin: str) -> bool:
        """Set or update a student's PIN."""
        try:
            ok = requests.post(self.webhook_url, json={
                "action":     "setPin",
                "reg_number": reg_number.strip().upper(),
                "new_pin":    new_pin.strip(),
            }, timeout=15).status_code == 200
            if ok:
                cached_fetch_roster.clear()
            return ok
        except:
            return False

    def reset_pin(self, reg_number: str, contact: str, new_pin: str) -> dict:
        """Reset PIN by verifying reg number + contact number."""
        try:
            r = requests.post(self.webhook_url, json={
                "action":     "resetPin",
                "reg_number": reg_number.strip().upper(),
                "contact":    contact.strip(),
                "new_pin":    new_pin.strip(),
            }, timeout=15)
            if r.status_code == 200:
                return r.json()
            return {"status": "error", "message": "Server error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Timetable ─────────────────────────────────────────────
    def fetch_timetable(self, dept: str = "ALL", year: str = "ALL") -> list:
        return cached_fetch_timetable(dept=dept, year=year)

    def add_timetable_entry(
        self, dept: str, year: str,
        day: str, time: str, course: str,
        lecturer: str = "", color: str = "",
        entry_type: str = "Weekly"
    ) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action":   "addTimetableEntry",
                "dept":     dept.strip().upper(),
                "year":     year.strip(),
                "day":      day.strip(),
                "time":     time.strip(),
                "course":   course.strip().upper(),
                "lecturer": lecturer.strip(),
                "color":    color.strip(),
                "type":     entry_type.strip(),
            }, timeout=15).status_code == 200
            if ok: cached_fetch_timetable.clear()
            return ok
        except:
            return False

    def delete_timetable_entry(
        self, dept: str, year: str,
        day: str, time: str
    ) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action": "deleteTimetableEntry",
                "dept":   dept.strip().upper(),
                "year":   year.strip(),
                "day":    day.strip(),
                "time":   time.strip(),
            }, timeout=15).status_code == 200
            if ok: cached_fetch_timetable.clear()
            return ok
        except:
            return False

    def clear_timetable(self, dept: str, year: str) -> bool:
        try:
            ok = requests.post(self.webhook_url, json={
                "action": "clearTimetable",
                "dept":   dept.strip().upper(),
                "year":   year.strip(),
            }, timeout=15).status_code == 200
            if ok: cached_fetch_timetable.clear()
            return ok
        except:
            return False