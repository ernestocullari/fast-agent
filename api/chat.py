from flask import Flask, request, jsonify
import traceback
import sys
import os

app = Flask(__name__)


@app.route("/api/chat", methods=["POST", "GET"])
def chat():
    try:
        # Basic test response to confirm endpoint works
        if request.method == "GET":
            return jsonify(
                {
                    "status": "debug_mode",
                    "message": "Chat endpoint is responding",
                    "method": "GET",
                    "python_version": sys.version,
                    "working_directory": os.getcwd(),
                }
            )

        # Handle POST requests
        try:
            data = request.get_json() or {}
        except Exception as e:
            return jsonify(
                {"error": "JSON parsing failed", "details": str(e), "raw_data": str(request.data)}
            ), 400

        # Test Google Sheets import specifically
        try:
            from googleapiclient.discovery import build
            from google.oauth2.service_account import Credentials

            sheets_import_status = "✅ Google Sheets imports successful"
        except Exception as e:
            sheets_import_status = f"❌ Google Sheets import failed: {str(e)}"

        # Test environment variables
        required_env_vars = ["GOOGLE_PRIVATE_KEY", "GOOGLE_CLIENT_EMAIL", "GOOGLE_SHEET_ID"]
        env_status = {}
        for var in required_env_vars:
            env_status[var] = "✅ Present" if os.getenv(var) else "❌ Missing"

        return jsonify(
            {
                "status": "debug_success",
                "request_data": data,
                "sheets_import": sheets_import_status,
                "environment_variables": env_status,
                "message": "Debug endpoint working - ready for full implementation",
            }
        )

    except Exception as e:
        # Comprehensive error logging
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc(),
            "python_path": sys.path,
            "environment": dict(os.environ),
        }
        return jsonify({"debug_error": error_details}), 500


if __name__ == "__main__":
    app.run(debug=True)
