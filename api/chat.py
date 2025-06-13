from http.server import BaseHTTPRequestHandler
import json
import os


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - Health check"""
        try:
            response = {
                "success": True,
                "status": "healthy",
                "agent": "artemis",
                "message": "🚀 Optimized MCP Geotargeting Server is running!",
                "version": "minimal_working",
                "timestamp": "2025-06-12",
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")

    def do_POST(self):
        """Handle POST requests - Chat functionality"""
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

            # Simple test response
            response = {
                "success": True,
                "response": f"Artemis received: '{message}'. Google Sheets integration will be added next.",
                "agent": "artemis",
                "session_id": session_id,
                "status": "minimal_working",
                "received_message": message,
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
