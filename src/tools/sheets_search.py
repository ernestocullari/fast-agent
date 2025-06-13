import os
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account
from difflib import SequenceMatcher


class SheetsSearcher:
    def __init__(self):
        self.service = None
        self.sheet_id = None
        self._setup_sheets_api()

    def _setup_sheets_api(self):
        """Initialize Google Sheets API with service account credentials"""
        try:
            # Get credentials from environment variables
            client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
            private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
            self.sheet_id = os.getenv("GOOGLE_SHEET_ID")

            if not all([client_email, private_key, self.sheet_id]):
                raise ValueError("Missing required Google Sheets credentials")

            # Create credentials
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

            # Build service
            self.service = build("sheets", "v4", credentials=credentials)

        except Exception as e:
            print(f"Error setting up Google Sheets API: {e}")
            raise

    def search_demographics(self, query):
        """Search demographics data with 4-level priority"""
        try:
            # Get sheet data
            sheet = self.service.spreadsheets()
            result = (
                sheet.values()
                .get(
                    spreadsheetId=self.sheet_id,
                    range="A:D",  # Category, Grouping, Demographic, Description
                )
                .execute()
            )

            values = result.get("values", [])
            if not values:
                return {"error": "No data found in sheet"}

            # Headers are in first row
            headers = values[0]
            data_rows = values[1:]

            # Find column indices
            category_idx = headers.index("Category") if "Category" in headers else 0
            grouping_idx = headers.index("Grouping") if "Grouping" in headers else 1
            demographic_idx = headers.index("Demographic") if "Demographic" in headers else 2
            description_idx = headers.index("Description") if "Description" in headers else 3

            # 4-level search priority
            matches = []

            # 1. Search Description first (highest priority)
            matches = self._search_column(data_rows, description_idx, query, headers)
            search_source = "Description"

            if not matches:
                # 2. Search Demographic
                matches = self._search_column(data_rows, demographic_idx, query, headers)
                search_source = "Demographic"

            if not matches:
                # 3. Search Grouping
                matches = self._search_column(data_rows, grouping_idx, query, headers)
                search_source = "Grouping"

            if not matches:
                # 4. Search Category
                matches = self._search_column(data_rows, category_idx, query, headers)
                search_source = "Category"

            if matches:
                # Format results as pathways
                pathways = []
                for match in matches[:3]:  # Top 3 matches
                    pathway = (
                        f"{match[category_idx]} → {match[grouping_idx]} → {match[demographic_idx]}"
                    )
                    pathways.append(pathway)

                return {
                    "success": True,
                    "pathways": pathways,
                    "search_source": search_source,
                    "query": query,
                }
            else:
                return {
                    "success": False,
                    "message": "No matching demographics found. Try rephrasing your audience description.",
                    "query": query,
                }

        except Exception as e:
            return {"success": False, "error": f"Error searching demographics: {str(e)}"}

    def _search_column(self, data_rows, column_idx, query, headers):
        """Search specific column with similarity matching"""
        matches = []
        query_lower = query.lower()

        for row in data_rows:
            if len(row) > column_idx:
                cell_value = str(row[column_idx]).lower()

                # Check for exact word matches or high similarity
                if (
                    query_lower in cell_value
                    or any(word in cell_value for word in query_lower.split())
                    or SequenceMatcher(None, query_lower, cell_value).ratio() > 0.6
                ):
                    matches.append(row)

        return matches
