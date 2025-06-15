from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Simple health check with basic Google Sheets test
        result = {
            "status": "testing_step_by_step", 
            "message": "Debugging Google Sheets integration",
            "agent": "artemis_debug"
        }
        
        try:
            # Test 1: Basic imports
            from googleapiclient.discovery import build
            from google.oauth2 import service_account
            result["step1_imports"] = "✅ Success"
            
            # Test 2: Environment variables
            client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
            private_key = os.getenv("GOOGLE_PRIVATE_KEY")
            sheet_id = os.getenv("GOOGLE_SHEET_ID")
            
            result["step2_env_vars"] = {
                "has_email": bool(client_email),
                "has_key": bool(private_key and len(private_key) > 100),
                "has_sheet_id": bool(sheet_id)
            }
            
            # Test 3: Try credential creation (but don't make API call yet)
            if all([client_email, private_key, sheet_id]):
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
                result["step3_credentials"] = "✅ Success"
                
                # Test 4: Build service (but don't call API yet)
                service = build("sheets", "v4", credentials=credentials)
                result["step4_service"] = "✅ Success"
                result["google_sheets_ready"] = True
            else:
                result["step3_credentials"] = "❌ Missing credentials"
                result["google_sheets_ready"] = False
                
        except Exception as e:
            result["error"] = str(e)
            result["error_type"] = type(e).__name__
            result["google_sheets_ready"] = False
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode("utf-8"))
            
            message = body.get("query", body.get("message", "")).strip()
            
            # For now, just return hardcoded response while we debug
            if "hardwood" in message.lower():
                response_text = """Based on your audience description, here are the targeting pathways:

**1.** Mobile Location Models → Store Visitors → Hardwood Floor Shoppers
   _Indicates consumer's likelihood to visit Hardwood Floor Shopping. A predictive model based on store visit patterns._

**2.** Mobile Location Models → Store Visitors → High End Furniture Shopper  
   _Consumer is likely to shop at a high-end furniture store. Predictive, statistical analysis based on mobile device data._

These pathways work together to effectively reach your target audience."""
                success = True
            else:
                response_text = f"Debug version received: '{message}

cat > api/chat.py << 'EOF'
from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Simple health check with basic Google Sheets test
        result = {
            "status": "testing_step_by_step", 
            "message": "Debugging Google Sheets integration",
            "agent": "artemis_debug"
        }
        
        try:
            # Test 1: Basic imports
            from googleapiclient.discovery import build
            from google.oauth2 import service_account
            result["step1_imports"] = "✅ Success"
            
            # Test 2: Environment variables
            client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
            private_key = os.getenv("GOOGLE_PRIVATE_KEY")
            sheet_id = os.getenv("GOOGLE_SHEET_ID")
            
            result["step2_env_vars"] = {
                "has_email": bool(client_email),
                "has_key": bool(private_key and len(private_key) > 100),
                "has_sheet_id": bool(sheet_id)
            }
            
            # Test 3: Try credential creation (but don't make API call yet)
            if all([client_email, private_key, sheet_id]):
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
                result["step3_credentials"] = "✅ Success"
                
                # Test 4: Build service (but don't call API yet)
                service = build("sheets", "v4", credentials=credentials)
                result["step4_service"] = "✅ Success"
                result["google_sheets_ready"] = True
            else:
                result["step3_credentials"] = "❌ Missing credentials"
                result["google_sheets_ready"] = False
                
        except Exception as e:
            result["error"] = str(e)
            result["error_type"] = type(e).__name__
            result["google_sheets_ready"] = False
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode("utf-8"))
            
            message = body.get("query", body.get("message", "")).strip()
            
            # For now, just return hardcoded response while we debug
            if "hardwood" in message.lower():
                response_text = """Based on your audience description, here are the targeting pathways:

**1.** Mobile Location Models → Store Visitors → Hardwood Floor Shoppers
   _Indicates consumer's likelihood to visit Hardwood Floor Shopping. A predictive model based on store visit patterns._

**2.** Mobile Location Models → Store Visitors → High End Furniture Shopper  
   _Consumer is likely to shop at a high-end furniture store. Predictive, statistical analysis based on mobile device data._

These pathways work together to effectively reach your target audience."""
                success = True
            else:
                response_text = f"Debug version received: '{message}'. Try 'hardwood floors' or contact ernesto@artemistargeting.com"
                success = False
            
            response = {
                "success": success,
                "response": response_text,
                "agent": "artemis_debug_working",
                "session_id": body.get("session_id", "default"),
                "query": message,
                "debug": "minimal_version_for_testing"
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            error_response = {
                "success": False,
                "response": f"POST Error: {str(e)}",
                "agent": "artemis_error",
                "error_type": type(e).__name__
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
