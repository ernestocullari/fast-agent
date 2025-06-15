from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        import_results = {}
        
        # Test basic imports
        try:
            import os
            import_results["os"] = "✅ Success"
        except Exception as e:
            import_results["os"] = f"❌ {str(e)}"
            
        # Test Google API imports
        try:
            from googleapiclient.discovery import build
            import_results["googleapiclient"] = "✅ Success"
        except Exception as e:
            import_results["googleapiclient"] = f"❌ {str(e)}"
            
        try:
            from google.oauth2 import service_account
            import_results["google.oauth2"] = "✅ Success"
        except Exception as e:
            import_results["google.oauth2"] = f"❌ {str(e)}"
        
        response = {
            "test": "vercel_python_environment",
            "import_results": import_results,
            "python_path": __file__
        }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
