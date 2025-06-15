from http.server import BaseHTTPRequestHandler
import json
import os
import time

# Try to import Google Sheets dependencies
try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# INLINE Google Sheets functionality - no separate imports needed
def get_sheets_data():
    """Get data from Google Sheets - inline function"""
    if not GOOGLE_AVAILABLE:
        return None
        
    try:
        client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
        private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
        sheet_id = os.getenv("GOOGLE_SHEET_ID")

        if not all([client_email, private_key, sheet_id]):
            return None

        credentials_info = {
            "type": "service_account",
            "client_email": client_email,
            "private_key": private_key,
            "private_key_id": "1",
            "client_id": "1",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }

        credentials = service_account.Credentials.from_service_account_info(
            credentials_info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )

        service = build("sheets", "v4", credentials=credentials)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=sheet_id, range="A:D").execute()

        values = result.get("values", [])
        if not values:
            return None

        headers = values[0]
        data_rows = values[1:]

        # Process the data
        sheets_data = []
        for row in data_rows:
            if len(row) >= 4:
                row_dict = {
                    "Category":
cat > requirements.txt << 'EOF'
google-api-python-client==2.88.0
google-auth==2.17.3
google-auth-oauthlib==1.0.0
google-auth-httplib2==0.1.0
cachetools==5.3.0
