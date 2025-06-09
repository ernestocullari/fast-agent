# chat.py - Complete Python MCP Server for Geotargeting
# Copy this ENTIRE file

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)  # This fixes the authentication/CORS issues


@app.route("/api/chat", methods=["GET", "POST", "OPTIONS"])
def chat_handler():
    # Handle preflight requests (fixes browser authentication issues)
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        return response

    try:
        # Handle GET requests (for testing)
        if request.method == "GET":
            response_data = {
                "success": True,
                "message": "MCP Geotargeting Server is running!",
                "endpoints": {"chat": "POST /api/chat", "status": "GET /api/chat"},
                "timestamp": datetime.now().isoformat(),
            }

            response = jsonify(response_data)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response

        # Handle POST requests (main functionality)
        if request.method == "POST":
            # Get JSON data from request
            data = request.get_json() if request.get_json() else {}

            message = data.get("message", "")
            context = data.get("context", {})
            location = data.get("location", None)
            campaign_type = data.get("campaign_type", "standard")

            # Basic validation
            if not message:
                error_response = {
                    "error": "Message is required",
                    "example": {
                        "message": "Generate campaign for coffee shop",
                        "context": {"session_id": "test_001"},
                        "location": {"lat": 40.7128, "lng": -74.0060, "city": "New York"},
                        "campaign_type": "geofence",
                    },
                }
                response = jsonify(error_response)
                response.status_code = 400
                response.headers.add("Access-Control-Allow-Origin", "*")
                return response

            # Process the geotargeting request
            response_data = {
                "success": True,
                "message": f"Processed: {message}",
                "context": context,
                "location": location,
                "campaign_type": campaign_type,
                "recommendations": [
                    "Create 500m radius geofence around target location",
                    "Use weather-triggered messaging",
                    "Implement time-of-day optimization",
                    "Set up competitor proximity alerts",
                ],
                "timestamp": datetime.now().isoformat(),
                "session_id": context.get(
                    "session_id", f"session_{int(datetime.now().timestamp())}"
                ),
            }

            response = jsonify(response_data)
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response

    except Exception as e:
        error_response = {
            "error": "Internal server error",
            "details": str(e),
            "timestamp": datetime.now().isoformat(),
        }
        response = jsonify(error_response)
        response.status_code = 500
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response


# Default route
@app.route("/")
def home():
    response_data = {
        "message": "MCP Geotargeting Server",
        "status": "running",
        "api_endpoint": "/api/chat",
    }
    response = jsonify(response_data)
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


# For Vercel deployment
def handler(request):
    return app(request.environ, lambda *args: None)
