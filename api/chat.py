# api/chat.py - MCP Server with n8n Workflow Integration

from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime
import requests
import os
import re


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

        response = {
            "success": True,
            "message": "🚀 MCP Geotargeting Server with n8n Integration is running!",
            "endpoints": {"chat": "POST /chat", "status": "GET /"},
            "features": [
                "n8n workflow integration",
                "Google Sheets targeting data",
                "Category selection assistance",
                "Demographic targeting help",
                "Context-aware recommendations",
            ],
            "timestamp": datetime.now().isoformat(),
            "method": "GET",
        }

        self.wfile.write(json.dumps(response).encode())
        return

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

        try:
            # Get POST data
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            # Parse JSON
            try:
                data = json.loads(post_data.decode("utf-8")) if post_data else {}
            except:
                data = {}

            message = data.get("message", "")
            context = data.get("context", {})
            location = data.get("location", None)
            campaign_type = data.get("campaign_type", "standard")

            # Basic validation
            if not message:
                response = {
                    "error": "Message is required",
                    "example": {
                        "message": "I want to target coffee shop customers",
                        "context": {"session_id": "test_001"},
                        "location": {"lat": 40.7128, "lng": -74.0060, "city": "New York"},
                        "campaign_type": "geofence",
                    },
                }
                self.wfile.write(json.dumps(response).encode())
                return

            # Try n8n workflow first, then fallback to direct processing
            n8n_response = self.call_n8n_workflow(message, context, location, campaign_type)

            if n8n_response.get("success"):
                # Use n8n workflow response
                response = n8n_response
            else:
                # Fallback to direct Google Sheets processing
                sheets_data = self.get_google_sheets_data()
                suggested_selections = self.analyze_message_and_suggest(message, sheets_data)
                recommendations = self.generate_contextual_recommendations(
                    message, location, campaign_type, suggested_selections
                )

                response = {
                    "success": True,
                    "message": f"Processed: {message}",
                    "context": context,
                    "location": location,
                    "campaign_type": campaign_type,
                    "suggested_selections": suggested_selections,
                    "recommendations": recommendations,
                    "available_options": self.get_available_options(sheets_data),
                    "timestamp": datetime.now().isoformat(),
                    "session_id": context.get(
                        "session_id", f"session_{int(datetime.now().timestamp())}"
                    ),
                    "method": "POST",
                    "source": "fallback_processing",
                }

            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            response = {
                "error": "Internal server error",
                "details": str(e),
                "timestamp": datetime.now().isoformat(),
            }
            self.wfile.write(json.dumps(response).encode())

    def call_n8n_workflow(self, message, context=None, location=None, campaign_type="standard"):
        """Call the n8n MCP Server workflow"""
        try:
            # Get n8n webhook URL from environment variable
            n8n_webhook_url = os.environ.get("N8N_WEBHOOK_URL")

            if not n8n_webhook_url:
                # Default to a placeholder - you'll need to set this
                n8n_webhook_url = (
                    "https://YOUR-N8N-INSTANCE.app.n8n.cloud/webhook/YOUR-WEBHOOK-PATH"
                )

                return {
                    "success": False,
                    "error": "N8N_WEBHOOK_URL environment variable not set",
                    "note": "Falling back to direct processing",
                }

            payload = {
                "message": message,
                "context": context or {},
                "location": location,
                "campaign_type": campaign_type,
                "timestamp": datetime.now().isoformat(),
                "source": "vercel_mcp_server",
            }

            print(f"Calling n8n workflow: {n8n_webhook_url}")
            response = requests.post(n8n_webhook_url, json=payload, timeout=30)

            if response.status_code == 200:
                n8n_data = response.json()
                return {
                    "success": True,
                    "message": f"n8n processed: {message}",
                    "context": context,
                    "location": location,
                    "campaign_type": campaign_type,
                    "suggested_selections": n8n_data.get("suggested_selections", {}),
                    "recommendations": n8n_data.get("recommendations", []),
                    "available_options": n8n_data.get("available_options", {}),
                    "timestamp": datetime.now().isoformat(),
                    "session_id": context.get(
                        "session_id", f"session_{int(datetime.now().timestamp())}"
                    )
                    if context
                    else f"session_{int(datetime.now().timestamp())}",
                    "method": "POST",
                    "source": "n8n_workflow",
                }
            else:
                return {
                    "success": False,
                    "error": f"n8n workflow returned status {response.status_code}",
                    "response_text": response.text[:200] if response.text else "No response text",
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "n8n workflow timeout (30s)",
                "note": "Workflow may be running but took too long to respond",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"n8n call failed: {str(e)}",
                "note": "Falling back to direct processing",
            }

    def get_google_sheets_data(self):
        """Fetch data from Google Sheets (fallback method)"""
        try:
            sheets_url = os.environ.get("GOOGLE_SHEETS_URL")

            if not sheets_url:
                return {
                    "error": "Google Sheets URL not configured",
                    "sample_data": self.get_sample_data(),
                }

            response = requests.get(sheets_url, timeout=10)

            if response.status_code == 200:
                lines = response.text.strip().split("\n")
                if len(lines) < 2:
                    return {"error": "No data found in Google Sheets"}

                headers = [h.strip().strip('"') for h in lines[0].split(",")]

                data = []
                for line in lines[1:]:
                    # Handle CSV with quoted fields
                    fields = []
                    current_field = ""
                    in_quotes = False

                    for char in line:
                        if char == '"':
                            in_quotes = not in_quotes
                        elif char == "," and not in_quotes:
                            fields.append(current_field.strip().strip('"'))
                            current_field = ""
                        else:
                            current_field += char

                    fields.append(current_field.strip().strip('"'))

                    if len(fields) >= len(headers):
                        row_data = dict(zip(headers, fields))
                        data.append(row_data)

                return {"success": True, "data": data, "headers": headers}
            else:
                return {
                    "error": f"Failed to fetch Google Sheets: {response.status_code}",
                    "sample_data": self.get_sample_data(),
                }

        except Exception as e:
            return {
                "error": f"Google Sheets error: {str(e)}",
                "sample_data": self.get_sample_data(),
            }

    def get_sample_data(self):
        """Return sample data if Google Sheets is not available"""
        return [
            {
                "Category": "Retail",
                "Grouping": "Food & Beverage",
                "Demographic": "Young Professionals",
                "Description": "Ages 25-35, high income, urban lifestyle",
            },
            {
                "Category": "Service",
                "Grouping": "Professional Services",
                "Demographic": "Business Owners",
                "Description": "Small business owners, decision makers",
            },
            {
                "Category": "Entertainment",
                "Grouping": "Dining",
                "Demographic": "Families",
                "Description": "Families with children, weekend activities",
            },
        ]

    def analyze_message_and_suggest(self, message, sheets_data):
        """Analyze user message and suggest appropriate selections (fallback method)"""
        message_lower = message.lower()

        data = sheets_data.get("data", self.get_sample_data())

        suggestions = {
            "categories": [],
            "groupings": [],
            "demographics": [],
            "descriptions": [],
            "reasoning": [],
        }

        # Keywords mapping
        keyword_mappings = {
            "coffee": ["Food & Beverage", "Young Professionals", "Retail"],
            "restaurant": ["Food & Beverage", "Families", "Dining"],
            "shop": ["Retail", "Shoppers", "Consumer Goods"],
            "gym": ["Health & Fitness", "Health Conscious", "Service"],
            "salon": ["Personal Care", "Beauty Enthusiasts", "Service"],
            "office": ["Professional Services", "Business Owners", "Service"],
            "family": ["Families", "Family Entertainment", "Entertainment"],
            "young": ["Young Professionals", "Students", "Millennials"],
            "business": ["Business Owners", "Professional Services", "B2B"],
        }

        # Find matches
        for keyword, related_terms in keyword_mappings.items():
            if keyword in message_lower:
                suggestions["reasoning"].append(f"Detected '{keyword}' in your message")

                for row in data:
                    for term in related_terms:
                        if term.lower() in row.get("Category", "").lower():
                            if row["Category"] not in suggestions["categories"]:
                                suggestions["categories"].append(row["Category"])

                        if term.lower() in row.get("Grouping", "").lower():
                            if row["Grouping"] not in suggestions["groupings"]:
                                suggestions["groupings"].append(row["Grouping"])

                        if term.lower() in row.get("Demographic", "").lower():
                            if row["Demographic"] not in suggestions["demographics"]:
                                suggestions["demographics"].append(row["Demographic"])

        # If no specific matches, provide general suggestions
        if not any(
            [suggestions["categories"], suggestions["groupings"], suggestions["demographics"]]
        ):
            suggestions["categories"] = [row["Category"] for row in data[:3]]
            suggestions["groupings"] = [row["Grouping"] for row in data[:3]]
            suggestions["demographics"] = [row["Demographic"] for row in data[:3]]
            suggestions["reasoning"].append("Based on common geotargeting options")

        return suggestions

    def get_available_options(self, sheets_data):
        """Get all available options from the Google Sheet (fallback method)"""
        data = sheets_data.get("data", self.get_sample_data())

        options = {
            "categories": list(
                set([row.get("Category", "") for row in data if row.get("Category")])
            ),
            "groupings": list(
                set([row.get("Grouping", "") for row in data if row.get("Grouping")])
            ),
            "demographics": list(
                set([row.get("Demographic", "") for row in data if row.get("Demographic")])
            ),
            "descriptions": [row.get("Description", "") for row in data if row.get("Description")],
        }

        return options

    def generate_contextual_recommendations(self, message, location, campaign_type, selections):
        """Generate recommendations based on selections (fallback method)"""

        base_recommendations = [
            "Create 500m radius geofence around target location",
            "Use weather-triggered messaging",
            "Implement time-of-day optimization",
            "Set up competitor proximity alerts",
        ]

        contextual_recommendations = []

        # Add recommendations based on selections
        if selections.get("categories"):
            for category in selections["categories"][:2]:
                contextual_recommendations.append(
                    f"Optimize campaigns for {category} sector patterns"
                )

        if selections.get("demographics"):
            for demographic in selections["demographics"][:2]:
                contextual_recommendations.append(
                    f"Target {demographic} with personalized messaging"
                )

        if selections.get("groupings"):
            for grouping in selections["groupings"][:1]:
                contextual_recommendations.append(
                    f"Focus on {grouping} specific timing and locations"
                )

        # Location-specific recommendations
        if location and location.get("city"):
            contextual_recommendations.append(
                f"Apply {location['city']}-specific demographic insights"
            )

        # Combine and limit recommendations
        all_recommendations = base_recommendations + contextual_recommendations
        return all_recommendations[:8]

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        return
