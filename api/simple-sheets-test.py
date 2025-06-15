from http.server import BaseHTTPRequestHandler
import json
import os
import traceback


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Test Google Sheets connection
            from googleapiclient.discovery import build
            from google.oauth2.service_account import Credentials

            # Get environment variables
            private_key = os.getenv("GOOGLE_PRIVATE_KEY")
            client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
            sheet_id = os.getenv("GOOGLE_SHEET_ID")

            if not all([private_key, client_email, sheet_id]):
                result = {
                    "error": "Missing environment variables",
                    "private_key_present": bool(private_key),
                    "client_email_present": bool(client_email),
                    "sheet_id_present": bool(sheet_id),
                }
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                return

            # Create credentials
            creds_info = {
                "type": "service_account",
                "project_id": "quick-website-dev",
                "private_key_id": "key_id_placeholder",
                "private_key": private_key.replace("\\n", "\n"),
                "client_email": client_email,
                "client_id": "client_id_placeholder",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }

            credentials = Credentials.from_service_account_info(
                creds_info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
            )

            # Build service
            service = build("sheets", "v4", credentials=credentials)

            # Try to read first few rows
            range_name = "Sheet1!A1:D10"  # Category, Grouping, Demographic, Description
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=sheet_id, range=range_name)
                .execute()
            )

            values = result.get("values", [])

            response_data = {
                "status": "✅ SUCCESS",
                "message": "Google Sheets connection working",
                "rows_found": len(values),
                "sample_data": values[:3] if values else [],
                "sheet_id": sheet_id[:10] + "...",
                "credentials_working": True,
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())

        except Exception as e:
            error_result = {
                "status": "❌ FAILED",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "environment_check": {
                    "private_key_length": len(os.getenv("GOOGLE_PRIVATE_KEY", "")),
                    "client_email": os.getenv("GOOGLE_CLIENT_EMAIL", "not_set"),
                    "sheet_id": os.getenv("GOOGLE_SHEET_ID", "not_set"),
                },
            }

            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(error_result).encode())
