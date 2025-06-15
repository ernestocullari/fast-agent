import json
import os
import traceback


def handler(req, res):
    try:
        # Test Google Sheets connection
        from googleapiclient.discovery import build
        from google.oauth2.service_account import Credentials

        # Get environment variables
        private_key = os.getenv("GOOGLE_PRIVATE_KEY")
        client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
        sheet_id = os.getenv("GOOGLE_SHEET_ID")

        if not all([private_key, client_email, sheet_id]):
            res.status(400).json(
                {
                    "error": "Missing environment variables",
                    "private_key_present": bool(private_key),
                    "client_email_present": bool(client_email),
                    "sheet_id_present": bool(sheet_id),
                }
            )
            return

        # Create credentials
        creds_info = {
            "type": "service_account",
            "project_id": "quick-website-dev",
            "private_key_id": "key_id_placeholder",
            "private_key": private_key.replace("\\n", "\n"),
            "client_email": client_email,
            "client_id": "client_id_placeholder",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }

        credentials = Credentials.from_service_account_info(
            creds_info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )

        # Build service
        service = build("sheets", "v4", credentials=credentials)

        # Try to read first few rows
        range_name = "Sheet1!A1:D10"  # Category, Grouping, Demographic, Description
        result = (
            service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_name).execute()
        )

        values = result.get("values", [])

        res.status(200).json(
            {
                "status": "✅ SUCCESS",
                "message": "Google Sheets connection working",
                "rows_found": len(values),
                "sample_data": values[:3] if values else [],
                "sheet_id": sheet_id[:10] + "...",  # Partial ID for security
                "credentials_working": True,
            }
        )

    except Exception as e:
        res.status(500).json(
            {
                "status": "❌ FAILED",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "environment_check": {
                    "private_key_length": len(os.getenv("GOOGLE_PRIVATE_KEY", "")),
                    "client_email": os.getenv("GOOGLE_CLIENT_EMAIL", "not_set"),
                    "sheet_id": os.getenv("GOOGLE_SHEET_ID", "not_set"),
                },
            }
        )
