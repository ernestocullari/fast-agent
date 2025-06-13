from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Debug credentials format"""
        try:
            client_email = os.getenv('GOOGLE_CLIENT_EMAIL')
            private_key = os.getenv('GOOGLE_PRIVATE_KEY', '')
            sheet_id = os.getenv('GOOGLE_SHEET_ID')
            
            response = {
                "has_client_email": bool(client_email),
                "client_email": client_email if client_email else "MISSING",
                "has_private_key": bool(private_key),
                "private_key_length": len(private_key),
                "private_key_starts_with": private_key[:80] if private_key else "MISSING",
                "private_key_has_begin": "-----BEGIN PRIVATE KEY-----" in private_key if private_key else False,
                "private_key_has_end": "-----END PRIVATE KEY-----" in private_key if private_key else False,
                "has_sheet_id": bool(sheet_id),
                "sheet_id": sheet_id if sheet_id else "MISSING",
                "all_env_vars": [key for key in os.environ.keys() if 'GOOGLE' in key]
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except Exception as e:
            error_response = {"error": str(e)}
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())
