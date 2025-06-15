from http.server import BaseHTTPRequestHandler
import json
import traceback
import sys
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Basic debug response
            result = {
                "status": "debug_working",
                "message": "Chat endpoint responding with correct BaseHTTPRequestHandler format",
                "method": "GET",
                "python_version": sys.version[:20],
                "working_directory": os.getcwd()[-30:]
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            error_result = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
            
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(error_result).encode())
    
    def do_POST(self):
        try:
            # Get request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8')) if post_data else {}
            except:
                data = {}
            
            # Test Google Sheets imports
            try:
                from googleapiclient.discovery import build
                from google.oauth2.service_account import Credentials
                sheets_import_status = "✅ Google Sheets imports successful"
            except Exception as e:
                sheets_import_status = f"❌ Google Sheets import failed: {str(e)}"
            
            # Check environment variables
            required_env_vars = ['GOOGLE_PRIVATE_KEY', 'GOOGLE_CLIENT_EMAIL', 'GOOGLE_SHEET_ID']
            env_status = {}
            for var in required_env_vars:
                value = os.getenv(var)
                env_status[var] = "✅ Present" if value else "❌ Missing"
            
            # Return debug information
            response_data = {
                "status": "debug_success",
                "request_data": data,
                "sheets_import": sheets_import_status,
                "environment_variables": env_status,
                "message": "Debug endpoint working - ready for full implementation"
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
            
        except Exception as e:
            error_result = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
            
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(error_result).encode())