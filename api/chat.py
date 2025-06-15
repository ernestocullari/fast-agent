from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_path = os.path.join(parent_dir, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

# Try to import our search function
SEARCH_AVAILABLE = False
search_sheets_data = None

try:
    from tools.sheets_search import search_sheets_data
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        response = {
            "status": "healthy", 
            "message": "Working version with Google Sheets integration",
            "agent": "artemis",
            "search_available": SEARCH_AVAILABLE,
            "has_credentials": bool(os.getenv("GOOGLE_SHEET_ID"))
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode("utf-8"))
            
            message = body.get("query", body.get("message", "")).strip()
            
            # Use Google Sheets if available, otherwise fallback to hardcoded
            if SEARCH_AVAILABLE and search_sheets_data:
                try:
                    search_result = search_sheets_data(message)
                    response_text = search_result.get("response", "No response generated")
                    success = search_result.get("success", False)
                except Exception as e:
                    # Fallback to hardcoded for "hardwood floors"
                    if "hardwood" in message.lower():
                        response_text = """Based on your audience description, here are the targeting pathways:

**1.** Mobile Location Models → Store Visitors → Hardwood Floor Shoppers
   _Indicates consumer's likelihood to visit Hardwood Floor Shopping. A predictive model based on store visit patterns._

**2.** Mobile Location Models → Store Visitors → High End Furniture Shopper  
   _Consumer is likely to shop at a high-end furniture store. Predictive,
cat > requirements.txt << 'EOF'
google-api-python-client==2.88.0
google-auth==2.17.3
google-auth-oauthlib==1.0.0
google-auth-httplib2==0.1.0
cachetools==5.3.0
