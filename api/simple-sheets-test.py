from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        result = {"test": "simple_google_sheets_test"}
        
        try:
            from googleapiclient.discovery import build
            from google.oauth2 import service_account
            result["imports"] = "✅ Success"
            
            # Test credentials
            client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
            private_key = os.getenv("GOOGLE_PRIVATE_KEY")
            sheet_id = os.getenv("GOOGLE_SHEET_ID")
            
            result["credentials"] = {
                "client_email_exists": bool(client_email),
                "private_key_exists": bool(private_key and len(private_key) > 100),
                "sheet_id_exists": bool(sheet_id)
            }
            
            if all([client_email, private_key, sheet_id]):
                result["can_attempt_connection"] = True
                
                # Try to create credentials
                credentials_info = {
                    "type": "service_account",
                    "client_email": client_email,
                    "private_key": private_key.replace("\\n", "\n"),
                    "private_key_id": "1",
                    "client_id": "1",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
                
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
                )
                result["credentials_created"] = "✅ Success"
                
                # Try to build service
                service = build("sheets", "v4", credentials=credentials)
                result["service_built"] = "✅ Success"
                
            else:
                result["can_attempt_connection"] = False
                result["missing_credentials"] = True
                
        except Exception as e:
            result["error"] = str(e)
            result["error_type"] = type(e).__name__
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
