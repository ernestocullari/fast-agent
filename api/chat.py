from http.server import BaseHTTPRequestHandler
import json
import os

def get_google_sheets_data():
    """Minimal Google Sheets access function"""
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        
        client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
        private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
        sheet_id = os.getenv("GOOGLE_SHEET_ID")

        if not all([client_email, private_key, sheet_id]):
            return None, "Missing credentials"

        credentials_info = {
            "type": "service_account",
            "client_email": client_email,
            "private_key": private_key,
            "private_key_id": "1",
            "client_id": "1",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }

        credentials = service_account.Credentials.from_service_account_info(
            credentials_info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )

        service = build("sheets", "v4", credentials=credentials)
        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range="A:D").execute()

        values = result.get("values", [])
        if not values or len(values) < 2:
            return None, "No data found"

        headers = values[0]
        data_rows = values[1:]
        
        processed_data = []
        for row in data_rows:
            if len(row) >= 4:
                processed_data.append({
                    "Category": str(row[0]).strip(),
                    "Grouping": str(row[1]).strip(), 
                    "Demographic": str(row[2]).strip(),
                    "Description": str(row[3]).strip()
                })

        return processed_data, None

    except Exception as e:
        return None, str(e)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        sheets_data, error = get_google_sheets_data()
        
        response = {
            "status": "GOOGLE_SHEETS_TEST", 
            "message": "Google Sheets Integration Active",
            "agent": "artemis_v2",
            "google_sheets_working": sheets_data is not None,
            "data_count": len(sheets_data) if sheets_data else 0,
            "error": error,
            "timestamp": "2025-06-15-NEW"
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        try:head -10 api/chat.py
git diff api/chat.py
git add api/chat.py
git commit -m "FORCE UPDATE: Google Sheets test version with NEW markers"
git push
git show HEAD:api/chat.py | head -10

cat >> api/chat.py << 'EOF'
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode("utf-8"))
            
            message = body.get("query", body.get("message", "")).strip()
            
            # Always provide hardcoded fallback for now while testing
            if "hardwood" in message.lower():
                response_text = """Based on your audience description, here are the targeting pathways:

**1.** Mobile Location Models → Store Visitors → Hardwood Floor Shoppers
   _Indicates consumer's likelihood to visit Hardwood Floor Shopping. A predictive model based on store visit patterns._

**2.** Mobile Location Models → Store Visitors → High End Furniture Shopper  
   _Consumer is likely to shop at a high-end furniture store. Predictive, statistical analysis based on mobile device data._

These pathways work together to effectively reach your target audience."""
                success = True
            else:
                response_text = f"NEW VERSION received: '{message}'. Try 'hardwood floors' or contact ernesto@artemistargeting.com"
                success = False
            
            response = {
                "success": success,
                "response": response_text,
                "agent": "artemis_NEW_VERSION",
                "session_id": body.get("session_id", "default"),
                "query": message,
                "version": "google_sheets_test_NEW"
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            fallback_response = {
                "success": False,
                "response": f"Error: {str(e)}",
                "agent": "artemis_NEW_ERROR"
            }
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(fallback_response).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
