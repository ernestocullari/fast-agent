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

try:
    from tools.sheets_search import search_sheets_data
    SEARCH_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    SEARCH_AVAILABLE = False

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - Health check"""
        try:
            response = {
                "success": True,
                "status": "healthy",
                "agent": "artemis",
                "message": "🚀 Enhanced Similarity Algorithm MCP Server is running!",
                "version": "enhanced_similarity_v2",
                "search_available": SEARCH_AVAILABLE,
                "has_sheets_credentials": bool(os.getenv("GOOGLE_SHEET_ID")),
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")

    def do_POST(self):
        """Handle POST requests - Chat with Enhanced Google Sheets search"""
        try:
            # Get request body
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            # Parse JSON
            try:
                body = json.loads(post_data.decode("utf-8"))
            except json.JSONDecodeError:
                body = {}

            # Accept both 'query' and 'message' parameters
            message = body.get("query", body.get("message", "")).strip()
            session_id = body.get("session_id", "default")

            if not message:
                error_response = {
                    "success": False,
                    "response": "No query provided",
                    "agent": "artemis",
                    "session_id": session_id
                }
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Search Google Sheets for demographics using enhanced algorithm
            if not SEARCH_AVAILABLE:
                response_message = "Search function not available due to import error. Please contact ernesto@artemistargeting.com"
                search_success = False
            else:
                try:
                    search_result = search_sheets_data(message)
                    response_message = search_result.get("response", "No response generated")
                    search_success = search_result.get("success", False)
                except Exception as e:
                    response_message = f"Error accessing demographics database: {str(e)}. Please contact ernesto@artemistargeting.com"
                    search_success = False

            response = {
                "success": search_success,
                "respon

cat > api/chat.py << 'EOF'
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

try:
    from tools.sheets_search import search_sheets_data
    SEARCH_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    SEARCH_AVAILABLE = False

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - Health check"""
        try:
            response = {
                "success": True,
                "status": "healthy",
                "agent": "artemis",
                "message": "🚀 Enhanced Similarity Algorithm MCP Server is running!",
                "version": "enhanced_similarity_v2",
                "search_available": SEARCH_AVAILABLE,
                "has_sheets_credentials": bool(os.getenv("GOOGLE_SHEET_ID")),
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")

    def do_POST(self):
        """Handle POST requests - Chat with Enhanced Google Sheets search"""
        try:
            # Get request body
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            # Parse JSON
            try:
                body = json.loads(post_data.decode("utf-8"))
            except json.JSONDecodeError:
                body = {}

            # Accept both 'query' and 'message' parameters
            message = body.get("query", body.get("message", "")).strip()
            session_id = body.get("session_id", "default")

            if not message:
                error_response = {
                    "success": False,
                    "response": "No query provided",
                    "agent": "artemis",
                    "session_id": session_id
                }
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Search Google Sheets for demographics using enhanced algorithm
            if not SEARCH_AVAILABLE:
                response_message = "Search function not available due to import error. Please contact ernesto@artemistargeting.com"
                search_success = False
            else:
                try:
                    search_result = search_sheets_data(message)
                    response_message = search_result.get("response", "No response generated")
                    search_success = search_result.get("success", False)
                except Exception as e:
                    response_message = f"Error accessing demographics database: {str(e)}. Please contact ernesto@artemistargeting.com"
                    search_success = False

            response = {
                "success": search_success,
                "response": response_message,
                "agent": "artemis",
                "session_id": session_id,
                "status": "enhanced_similarity_algorithm",
                "query": message,
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
                "response": f"Server error: {str(e)}",
                "agent": "artemis",
                "error": str(e)
            }
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
