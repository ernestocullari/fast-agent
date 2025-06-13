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

from tools.sheets_search import SheetsSearcher


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - Health check"""
        try:
            response = {
                "success": True,
                "status": "healthy",
                "agent": "artemis",
                "message": "🚀 Optimized MCP Geotargeting Server with Google Sheets is running!",
                "version": "google_sheets_integrated",
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
        """Handle POST requests - Chat with Google Sheets search"""
        try:
            # Get request body
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            # Parse JSON
            try:
                body = json.loads(post_data.decode("utf-8"))
            except json.JSONDecodeError:
                body = {}

            message = body.get("message", "No message provided")
            session_id = body.get("session_id", "default")

            # Search Google Sheets for demographics
            try:
                searcher = SheetsSearcher()
                search_result = searcher.search_demographics(message)

                if search_result.get("success"):
                    pathways = search_result.get("pathways", [])
                    search_source = search_result.get("search_source", "Unknown")

                    if pathways:
                        pathway_text = "\n".join(
                            [f"{i + 1}. **{pathway}**" for i, pathway in enumerate(pathways)]
                        )
                        response_message = f"Based on your audience description, here are the targeting pathways:\n\n{pathway_text}\n\nThese pathways work together to effectively reach your audience."
                    else:
                        response_message = "No specific targeting pathways found. Try describing your audience differently or contact ernesto@artemistargeting.com for consultation."
                else:
                    response_message = search_result.get(
                        "message", "Error searching for targeting options."
                    )

            except Exception as e:
                response_message = f"Error accessing demographics database: {str(e)}. Please contact ernesto@artemistargeting.com"

            response = {
                "success": True,
                "response": response_message,
                "agent": "artemis",
                "session_id": session_id,
                "status": "google_sheets_integrated",
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
                "error": f"Server error: {str(e)}",
                "agent": "artemis",
            }
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
