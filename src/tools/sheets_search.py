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
        """Strict search that ONLY returns actual Google Sheets data - NO FABRICATION"""
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
                return {"success": False, "error": "No data found in sheet"}

            # Headers are in first row
            headers = values[0]
            data_rows = values[1:]

            # Find column indices
            try:
                category_idx = headers.index("Category")
                grouping_idx = headers.index("Grouping")
                demographic_idx = headers.index("Demographic")
                description_idx = headers.index("Description")
            except ValueError as e:
                return {"success": False, "error": f"Required column not found: {e}"}

            # STRICT search - only return actual database matches
            matches = []
            query_lower = query.lower().strip()
            query_words = [word for word in query_lower.split() if len(word) > 2]

            for row in data_rows:
                if len(row) <= max(category_idx, grouping_idx, demographic_idx, description_idx):
                    continue

                category = str(row[category_idx]).strip() if len(row) > category_idx else ""
                grouping = str(row[grouping_idx]).strip() if len(row) > grouping_idx else ""
                demographic = (
                    str(row[demographic_idx]).strip() if len(row) > demographic_idx else ""
                )
                description = (
                    str(row[description_idx]).strip() if len(row) > description_idx else ""
                )

                # Skip empty rows
                if not any([category, grouping, demographic, description]):
                    continue

                # STRICT matching - must have clear relevance
                score = 0

                # Exact phrase match in description (highest priority)
                if query_lower in description.lower():
                    score += 10

                # Exact phrase match in demographic
                elif query_lower in demographic.lower():
                    score += 5

                # Individual word matching
                else:
                    word_matches = 0
                    for word in query_words:
                        if word in description.lower():
                            word_matches += 1
                        elif word in demographic.lower():
                            word_matches += 1

                    if word_matches >= len(query_words) * 0.7:  # At least 70% word match
                        score += word_matches

                # Only include high-confidence matches
                if score >= 3:
                    matches.append(
                        {
                            "row": row,
                            "score": score,
                            "category": category,
                            "grouping": grouping,
                            "demographic": demographic,
                            "description": description,
                        }
                    )

            # Process matches - ONLY return actual database data
            if matches:
                matches.sort(key=lambda x: x["score"], reverse=True)
                pathways = []
                seen_pathways = set()

                for match in matches[:5]:  # Check top 5 matches
                    if all([match["category"], match["grouping"], match["demographic"]]):
                        pathway = (
                            f"{match['category']} → {match['grouping']} → {match['demographic']}"
                        )
                        if pathway not in seen_pathways:
                            pathways.append(pathway)
                            seen_pathways.add(pathway)
                            if len(pathways) >= 3:  # Max 3 pathways
                                break

                if pathways:
                    return {
                        "success": True,
                        "pathways": pathways,
                        "search_source": "Google Sheets Database",
                        "query": query,
                        "matches_found": len(pathways),
                        "database_search": True,
                    }

            # NO FABRICATION - Clear failure message when no real matches found
            return {
                "success": False,
                "message": f"No targeting pathways found in our database for '{query}'. Please try describing your audience differently with terms like:\n\n• Specific demographics (age, income level)\n• Geographic preferences\n• Purchase behaviors or interests\n• Lifestyle characteristics\n\nFor personalized targeting consultation, contact ernesto@artemistargeting.com",
                "query": query,
                "search_attempted": True,
                "database_searched": True,
            }

        except Exception as e:
            return {"success": False, "error": f"Database search error: {str(e)}", "query": query}
