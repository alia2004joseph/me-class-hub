import pandas as pd
import requests
import base64   # Needed for encoding file bytes

class SheetDatabaseManager:
    """Handles secure REST API pipeline operations with Google Sheets Webhooks + Drive uploads."""

    def __init__(self):
        # Hardcoded to bypass secrets.toml typos permanently
        self.webhook_url = "https://script.google.com/macros/s/AKfycbyNSSTRMkXx3aQeK-9ow5xKACWYPnXkV8L-JGRNyLVkyXHx3gzViCJFGVJ3BhT1dg_h/exec"

    # ---------------------------
    # Student roster
    # ---------------------------
    def fetch_roster(self) -> pd.DataFrame:
        try:
            response = requests.get(self.webhook_url)
            if response.status_code == 200:
                data_json = response.json()
                if not data_json:
                    return self._get_empty_dataframe()
                return pd.DataFrame(data_json)
            return self._get_empty_dataframe()
        except:
            return self._get_empty_dataframe()

    def _get_empty_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(columns=["Timestamp", "Student Name", "Reg Number", "Course Code", "Contact", "Assigned Group"])

    # ---------------------------
    # Announcements
    # ---------------------------
    def fetch_announcements(self) -> list:
        """Downloads posted notices along with timestamps from the cloud."""
        try:
            target_url = f"{self.webhook_url}?action=getAnnouncements"
            response = requests.get(target_url)
            if response.status_code == 200:
                raw_list = response.json()
                clean_announcements = []
                if isinstance(raw_list, list):
                    for row in raw_list:
                        # Handle [timestamp, text] rows
                        if isinstance(row, list) and len(row) >= 2:
                            clean_announcements.append({
                                "timestamp": str(row[0]).strip(),
                                "text": str(row[1]).strip()
                            })
                        # Handle dicts
                        elif isinstance(row, dict):
                            clean_announcements.append({
                                "timestamp": str(row.get("timestamp", "")).strip(),
                                "text": str(row.get("text", "")).strip()
                            })
                        # Handle plain strings
                        elif isinstance(row, str):
                            clean_announcements.append({
                                "timestamp": "",
                                "text": row.strip()
                            })
                return clean_announcements[::-1]  # newest first
            return []
        except Exception as e:
            print("Fetch announcements error:", e)
            return []

    def post_announcement(self, text: str) -> bool:
        payload = {"action": "postAnnouncement", "text": text.strip()}
        try:
            return requests.post(self.webhook_url, json=payload).status_code == 200
        except:
            return False

    # ---------------------------
    # Student registration + deletion
    # ---------------------------
    def register_student(self, name: str, reg: str, code: str, contact: str) -> bool:
        name_parts = name.strip().split()
        if len(name_parts) >= 2:
            first_name = name_parts[0].upper()
            other_names = [part.title() for part in name_parts[1:]]
            clean_name = f"{first_name} {' '.join(other_names)}"
        elif len(name_parts) == 1:
            clean_name = name_parts[0].upper()
        else:
            clean_name = "Unknown"

        payload = {
            "action": "register",
            "student_name": clean_name,
            "reg_number": reg.strip().upper(),
            "course_code": code.strip().upper() if code else "UNASSIGNED",
            "contact": contact.strip(),
            "assigned_group": "Unassigned"
        }
        try:
            return requests.post(self.webhook_url, json=payload).status_code == 200
        except:
            return False

    def delete_student(self, name: str) -> dict:
        payload = {"action": "delete", "student_name": name.strip()}
        try:
            return requests.post(self.webhook_url, json=payload).json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ---------------------------
    # Group allocations
    # ---------------------------
    def save_group_allocations(self, allocations_dict: dict) -> dict:
        payload = {"action": "updateGroups", "allocations": allocations_dict}
        try:
            return requests.post(self.webhook_url, json=payload).json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ---------------------------
    # Materials (upload + fetch)
    # ---------------------------
    def upload_material(self, file_bytes, file_name: str, mime_type: str) -> bool:
        """Uploads a file to Google Drive via Apps Script backend."""
        try:
            encoded_file = base64.b64encode(file_bytes).decode("utf-8")
            payload = {
                "action": "upload_material",
                "file_name": file_name,
                "mime_type": mime_type,
                "file_data": encoded_file
            }
            response = requests.post(self.webhook_url, json=payload)
            if response.status_code == 200:
                result = response.json()
                return result.get("status") == "success"
            return False
        except Exception as e:
            print("Upload error:", e)
            return False
        
    def fetch_materials(self) -> list:
        """Fetch distributed course materials from Google Sheets via webhook."""
        try:
            target_url = f"{self.webhook_url}?action=getMaterials"
            response = requests.get(target_url)
            if response.status_code == 200:
                raw_list = response.json()
                materials = []
                if isinstance(raw_list, list):
                    for row in raw_list:
                        if isinstance(row, dict):
                            materials.append({
                                "name": row.get("name", "Unnamed"),
                                "url": row.get("url", "#")
                            })
                        elif isinstance(row, list) and len(row) >= 2:
                            materials.append({
                                "name": str(row[0]).strip(),
                                "url": str(row[1]).strip()
                            })
                return materials[::-1]
            return []
        except Exception as e:
            print("Fetch materials error:", e)
            return []
    def submit_feedback(self, reg_num: str, name: str, message: str) -> bool:
        """Sends student feedback message payload straight to the cloud."""
        payload = {
            "action": "postFeedback",
            "reg_number": reg_num,
            "student_name": name,
            "message": message.strip()
        }
        try:
            return requests.post(self.webhook_url, json=payload).status_code == 200
        except:
            return False

    def fetch_feedback(self) -> list:
        """Retrieves raw feedback message rows from the spreadsheet tracker."""
        try:
            target_url = f"{self.webhook_url}?action=getFeedback"
            response = requests.get(target_url)
            if response.status_code == 200:
                return response.json()[::-1]  # Newest messages show first
            return []
        except:
            return []
