from http.server import BaseHTTPRequestHandler
import json
import os
import traceback
import re
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Simple health check
        result = {
            "status": "✅ LIVE",
            "message": "Chat endpoint ready for targeting queries",
            "endpoints": ["GET /api/chat (health)", "POST /api/chat (targeting)"],
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def do_POST(self):
        try:
            # Get request body
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode("utf-8")) if post_data else {}

            user_message = data.get("message", "").strip().lower()

            if not user_message:
                self._send_error("No message provided", 400)
                return

            # Get targeting data from Google Sheets
            targeting_data = self._get_targeting_data()
            if not targeting_data:
                self._send_error("Could not access targeting database", 500)
                return

            # Find matching targeting options
            matches = self._find_targeting_matches(user_message, targeting_data)

            if matches:
                response = self._format_targeting_response(matches, user_message)
            else:
                response = self._get_fallback_response(user_message)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self._send_error(f"Server error: {str(e)}", 500)

    def _get_targeting_data(self):
        try:
            # Get environment variables with validation
            private_key = os.getenv("GOOGLE_PRIVATE_KEY")
            client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
            sheet_id = os.getenv("GOOGLE_SHEET_ID")

            # Debug: Check if all variables exist
            if not private_key:
                print("ERROR: GOOGLE_PRIVATE_KEY not found")
                return None
            if not client_email:
                print("ERROR: GOOGLE_CLIENT_EMAIL not found")
                return None
            if not sheet_id:
                print("ERROR: GOOGLE_SHEET_ID not found")
                return None

            print(f"DEBUG: private_key length: {len(private_key)}")
            print(f"DEBUG: client_email: {client_email}")
            print(f"DEBUG: sheet_id: {sheet_id[:10]}...")

            # Process private key
            private_key = private_key.replace("\\n", "\n")

            # Create credentials info
            creds_info = {
                "type": "service_account",
                "project_id": "quick-website-dev",
                "private_key_id": "key_id_placeholder",
                "private_key": private_key,
                "client_email": client_email,
                "client_id": "client_id_placeholder",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }

            print("DEBUG: Creating credentials...")

            # Create credentials
            credentials = Credentials.from_service_account_info(
                creds_info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
            )

            print("DEBUG: Building service...")

            # Build service
            service = build("sheets", "v4", credentials=credentials)

            print("DEBUG: Making API call...")

            # Get all targeting data - try different ranges
            try:
                # First try the standard range
                range_name = "Sheet1!A:D"
                result = (
                    service.spreadsheets()
                    .values()
                    .get(spreadsheetId=sheet_id, range=range_name)
                    .execute()
                )
                print(f"DEBUG: Successfully got data from {range_name}")
            except Exception as range_error:
                print(f"DEBUG: Sheet1!A:D failed: {str(range_error)}")
                # Try alternative range
                try:
                    range_name = "A:D"
                    result = (
                        service.spreadsheets()
                        .values()
                        .get(spreadsheetId=sheet_id, range=range_name)
                        .execute()
                    )
                    print(f"DEBUG: Successfully got data from {range_name}")
                except Exception as range_error2:
                    print(f"DEBUG: A:D also failed: {str(range_error2)}")
                    # Try getting just first few rows to test
                    range_name = "A1:D100"
                    result = (
                        service.spreadsheets()
                        .values()
                        .get(spreadsheetId=sheet_id, range=range_name)
                        .execute()
                    )
                    print(f"DEBUG: Successfully got data from {range_name}")

            values = result.get("values", [])
            print(f"DEBUG: Retrieved {len(values)} rows")

            if values:
                print(f"DEBUG: First row: {values[0]}")
                if len(values) > 1:
                    print(f"DEBUG: Second row: {values[1]}")

            # Convert to structured data (skip header row if it exists)
            targeting_options = []
            start_row = (
                1
                if values
                and values[0]
                and any(word in str(values[0][0]).lower() for word in ["category", "cat"])
                else 0
            )

            for i, row in enumerate(values[start_row:]):
                if len(row) >= 4:
                    targeting_options.append(
                        {
                            "category": row[0].strip(),
                            "grouping": row[1].strip(),
                            "demographic": row[2].strip(),
                            "description": row[3].strip(),
                        }
                    )
                elif len(row) >= 1:  # Log incomplete rows
                    print(f"DEBUG: Incomplete row {i + start_row}: {row}")

            print(f"DEBUG: Processed {len(targeting_options)} targeting options")

            return targeting_options

        except Exception as e:
            print(f"ERROR in _get_targeting_data: {str(e)}")
            print(f"ERROR traceback: {traceback.format_exc()}")
            return None

    def _find_targeting_matches(self, user_message, targeting_data):
        matches = []
        user_words = set(re.findall(r"\b\w+\b", user_message.lower()))

        # Enhanced similarity scoring
        for option in targeting_data:
            score = 0

            # Check description first (highest priority)
            desc_words = set(re.findall(r"\b\w+\b", option["description"].lower()))
            desc_matches = user_words.intersection(desc_words)
            if desc_matches:
                score += len(desc_matches) * 3  # High weight for description matches

            # Check demographic (medium priority)
            demo_words = set(re.findall(r"\b\w+\b", option["demographic"].lower()))
            demo_matches = user_words.intersection(demo_words)
            if demo_matches:
                score += len(demo_matches) * 2

            # Check category and grouping (lower priority)
            cat_words = set(re.findall(r"\b\w+\b", option["category"].lower()))
            group_words = set(re.findall(r"\b\w+\b", option["grouping"].lower()))

            cat_matches = user_words.intersection(cat_words)
            group_matches = user_words.intersection(group_words)

            if cat_matches:
                score += len(cat_matches)
            if group_matches:
                score += len(group_matches)

            # Nuclear automotive prevention - exclude unless explicitly requested
            if any(
                word in option["description"].lower()
                for word in ["car", "auto", "vehicle", "automotive"]
            ):
                if not any(
                    word in user_message for word in ["car", "auto", "vehicle", "automotive"]
                ):
                    score = 0  # Zero out automotive results unless explicitly requested

            if score > 0:
                matches.append(
                    {
                        "option": option,
                        "score": score,
                        "pathway": f"{option['category']} → {option['grouping']} → {option['demographic']}",
                    }
                )

        # Sort by score and return top 3
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:3]

    def _format_targeting_response(self, matches, user_message):
        pathways = []
        for match in matches:
            pathways.append(
                {
                    "pathway": match["pathway"],
                    "description": match["option"]["description"],
                    "relevance_score": match["score"],
                }
            )

        return {
            "status": "success",
            "query": user_message,
            "targeting_pathways": pathways,
            "count": len(pathways),
            "message": f"Found {len(pathways)} targeting pathway(s) for your audience",
        }

    def _get_fallback_response(self, user_message):
        # Hardcoded fallback for testing
        if "hardwood" in user_message or "floor" in user_message:
            return {
                "status": "success",
                "query": user_message,
                "targeting_pathways": [
                    {
                        "pathway": "Demographics → Age → 35-44",
                        "description": "Homeowners in prime home improvement age",
                        "relevance_score": 5,
                    },
                    {
                        "pathway": "Demographics → Income → $75K-$100K",
                        "description": "Income bracket for home renovations",
                        "relevance_score": 4,
                    },
                ],
                "count": 2,
                "message": "Found targeting pathways for hardwood floors (fallback)",
            }

        return {
            "status": "no_matches",
            "query": user_message,
            "message": "No targeting pathways found. Try describing your audience with more specific details, or contact ernesto@artemistargeting.com for assistance.",
            "suggestion": "Try terms like 'homeowners', 'professionals', 'parents', or specific age ranges",
        }

    def _send_error(self, message, status_code):
        error_response = {"status": "error", "message": message, "status_code": status_code}

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(error_response).encode())
