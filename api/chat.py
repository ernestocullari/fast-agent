import json
import traceback
import sys
import os


def handler(req, res):
    try:
        # Handle GET method for testing
        if req.method == "GET":
            result = {
                "status": "debug_mode",
                "message": "Chat endpoint responding correctly",
                "method": "GET",
                "python_version": sys.version[:20],
                "cwd": os.getcwd()[-30:],
            }

            res.status(200).json(result)
            return

        # Handle POST method
        try:
            # Get request body
            body = req.body if hasattr(req, "body") else {}
            if isinstance(body, str):
                data = json.loads(body) if body else {}
            else:
                data = body or {}
        except Exception as e:
            res.status(400).json({"error": "JSON parsing failed", "details": str(e)})
            return

        # Test Google Sheets imports
        try:
            from googleapiclient.discovery import build
            from google.oauth2.service_account import Credentials

            sheets_import_status = "✅ Google Sheets imports successful"
        except Exception as e:
            sheets_import_status = f"❌ Google Sheets import failed: {str(e)}"

        # Check environment variables
        required_env_vars = ["GOOGLE_PRIVATE_KEY", "GOOGLE_CLIENT_EMAIL", "GOOGLE_SHEET_ID"]
        env_status = {}
        for var in required_env_vars:
            value = os.getenv(var)
            env_status[var] = "✅ Present" if value else "❌ Missing"

        # Return debug information
        response_data = {
            "status": "debug_success",
            "request_data": data,
            "sheets_import": sheets_import_status,
            "environment_variables": env_status,
            "message": "Debug endpoint working - ready for full implementation",
        }

        res.status(200).json(response_data)

    except Exception as e:
        # Comprehensive error logging
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "function": "chat_handler_debug",
        }

        res.status(500).json({"debug_error": error_details})
