from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        response = {
            "status": "healthy", 
            "message": "Minimal working version",
            "agent": "artemis"
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
            
            # Hardcoded response for "hardwood floors" to test functionality
            if "hardwood" in message.lower():
                response_text = """Based on your audience description, here are the targeting pathways:

**1.** Mobile Location Models → Store Visitors → Hardwood Floor Shoppers
   _Indicates consumer's likelihood to visit Hardwood Floor Shopping. A predictive model based on store visit patterns._

**2.** Mobile Location Models → Store Visitors → High End Furniture Shopper  
   _Consumer is likely to shop at a high-end furniture store. Predictive, statistical analysis based on mobile device data._

These pathways work together to effectively reach your target audience."""
            else:
                response_text = f"I received your query: '{message}'. Try 'hardwood floors' for a sample response, or contact ernesto@artemistargeting.com for assistance."
            
            response = {
                "success": True,
                "response": response_text,
                "agent": "artemis",
                "session_id": body.get("session_id", "default"),
                "query": message
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
                "response": f"Error processing request: {str(e)}",
                "agent": "artemis"
            }
            self.send_response(500)
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
