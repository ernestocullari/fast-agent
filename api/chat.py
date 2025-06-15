from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        response = {
            "status": "healthy", 
            "message": "Stable working version",
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
            
            message = body.get("query", body.get("message", "")).strip().lower()
            
            # Enhanced hardcoded targeting database
            targeting_database = {
                "hardwood": {
                    "response": """Based on your audience description, here are the targeting pathways:

**1.** Mobile Location Models → Store Visitors → Hardwood Floor Shoppers
   _Indicates consumer's likelihood to visit Hardwood Floor Shopping. A predictive model based on store visit patterns._

**2.** Mobile Location Models → Store Visitors → High End Furniture Shopper  
   _Consumer is likely to shop at a high-end furniture store. Predictive, statistical analysis based on mobile device data._

**3.** Mobile Location Models → Store Visitors → Home Improvement Shoppers
   _Consumer is likely to shop at home improvement stores. Predictive, statistical analysis based on mobile device data._

These pathways work together to effectively reach your target audience."""
                },
                "home improvement": {
                    "response": """Based on your audience description, here are the targeting pathways:

**1.** Mobile Location Models → Store Visitors → Home Improvement Shoppers
   _Consumer is likely to shop at home improvement stores. Predictive, statistical analysis based on mobile device data._

**2.** Mobile Location Models → Store Visitors → Hardware Store Visitors
   _Indicates consumer's likelihood to visit hardware stores. A predictive model based on store visit patterns._

**3.** Consumer Models → Household → Homeowners
   _Targets households that own their homes. Predictive, statistical analysis based on property records._

These pathways work together to effectively reach your target audience."""
                },
                "fitness": {
                    "response": """Based on your audience description, here are the targeting pathways:

**1.** Mobile Location Models → Venue Visitors → Gym - Frequent Visitor
   _Consumer is likely to visit a gym. Predictive, statistical analysis based on mobile devices at a gym._

**2.** Consumer Models → Interest → Health & Fitness Enthusiasts
   _Indicates consumer's likelihood to be interested in health and fitness activities._

**3.** Mobile Location Models → Store Visitors → Sporting Goods Shoppers
   _Indicates consumer's likelihood to be sporting goods store visitors._

These pathways work together to effectively reach your target audience."""
                },
                "luxury": {
                    "response": """Based on your audience description, here are the targeting pathways:

**1.** Consumer Models → Financial → Affluent Households
   _Targets households with high income levels. Predictive, statistical analysis based on financial indicators._

**2.** Mobile Location Models → Store Visitors → Luxury Women's Retail Shoppers
   _Consumer is likely to shop at a luxury women's retail location._

**3.** Mobile Location Models → Store Visitors → High End Furniture Shopper
   _Consumer is likely to shop at a high-end furniture store._

These pathways work together to effectively reach your target audience."""
                }
            }
            
            # Find matching targeting pathways
            response_text = None
            for keyword, data in targeting_database.items():
                if keyword in message:
                    response_text = data["response"]
                    break
            
            if not response_text:
                response_text = f"I received your query: '{body.get('query', body.get('message', ''))}'. Try queries like 'hardwood floors', 'home improvement', 'fitness', or 'luxury' for sample targeting pathways, or contact ernesto@artemistargeting.com for assistance."
            
            response = {
                "success": True,
                "response": response_text,
                "agent": "artemis",
                "session_id": body.get("session_id", "default"),
                "query": body.get("query", body.get("message", ""))
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
# Force deployment Sun Jun 15 09:01:20 UTC 2025
