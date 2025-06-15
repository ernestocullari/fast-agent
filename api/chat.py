from http.server import BaseHTTPRequestHandler
import json
import os
import traceback
import re
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Health check endpoint
        result = {
            "status": "✅ LIVE",
            "message": "Artemis Targeting MCP Server - Universal Exact Matching",
            "version": "1.1.0",
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

            user_message = data.get("message", "").strip()

            if not user_message:
                self._send_error("No message provided", 400)
                return

            # Get targeting data from Google Sheets
            targeting_data = self._get_targeting_data()
            if not targeting_data:
                self._send_error("Could not access targeting database", 500)
                return

            # Find matching targeting options
            matches = self._find_targeting_matches(user_message.lower(), targeting_data)

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
            # Get environment variables
            private_key = os.getenv("GOOGLE_PRIVATE_KEY").replace("\\n", "\n")
            client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
            sheet_id = os.getenv("GOOGLE_SHEET_ID")

            # Create credentials
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

            credentials = Credentials.from_service_account_info(
                creds_info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
            )

            # Build service and get data
            service = build("sheets", "v4", credentials=credentials)

            # Try multiple range formats for compatibility
            for range_name in ["Sheet1!A:D", "A:D", "A1:D5000"]:
                try:
                    result = (
                        service.spreadsheets()
                        .values()
                        .get(spreadsheetId=sheet_id, range=range_name)
                        .execute()
                    )
                    break
                except:
                    continue

            values = result.get("values", [])

            # Convert to structured data (skip header row if it exists)
            targeting_options = []
            start_row = (
                1
                if values
                and values[0]
                and any(word in str(values[0][0]).lower() for word in ["category", "cat"])
                else 0
            )

            for row in values[start_row:]:
                if len(row) >= 4:
                    targeting_options.append(
                        {
                            "category": row[0].strip(),
                            "grouping": row[1].strip(),
                            "demographic": row[2].strip(),
                            "description": row[3].strip(),
                        }
                    )

            return targeting_options

        except Exception:
            return None

    def _find_targeting_matches(self, user_message, targeting_data):
        matches = []
        user_words = set(re.findall(r"\b\w+\b", user_message.lower()))

        # Universal exact matching algorithm
        for option in targeting_data:
            score = 0

            # PRIORITY 1: EXACT WORD MATCHING - Demographic Field (Highest Priority)
            demographic_lower = option["demographic"].lower()
            demographic_words = set(re.findall(r"\b\w+\b", demographic_lower))
            demo_exact_matches = user_words.intersection(demographic_words)
            if demo_exact_matches:
                score += (
                    len(demo_exact_matches) * 15
                )  # Very high score for demographic exact matches

                # Bonus for multiple word matches in same field
                if len(demo_exact_matches) > 1:
                    score += 10

            # PRIORITY 2: EXACT WORD MATCHING - Description Field (High Priority)
            description_lower = option["description"].lower()
            description_words = set(re.findall(r"\b\w+\b", description_lower))
            desc_exact_matches = user_words.intersection(description_words)
            if desc_exact_matches:
                score += len(desc_exact_matches) * 8  # High score for description exact matches

                # Bonus for multiple word matches in same field
                if len(desc_exact_matches) > 1:
                    score += 5

            # PRIORITY 3: EXACT WORD MATCHING - Category Field (Medium Priority)
            category_lower = option["category"].lower()
            category_words = set(re.findall(r"\b\w+\b", category_lower))
            cat_exact_matches = user_words.intersection(category_words)
            if cat_exact_matches:
                score += len(cat_exact_matches) * 6  # Medium score for category exact matches

            # PRIORITY 4: EXACT WORD MATCHING - Grouping Field (Medium Priority)
            grouping_lower = option["grouping"].lower()
            grouping_words = set(re.findall(r"\b\w+\b", grouping_lower))
            group_exact_matches = user_words.intersection(grouping_words)
            if group_exact_matches:
                score += len(group_exact_matches) * 6  # Medium score for grouping exact matches

            # PRIORITY 5: PHRASE MATCHING - Check for multi-word phrases
            all_text = f"{option['category']} {option['grouping']} {option['demographic']} {option['description']}".lower()

            # Extract potential phrases from user input (2-3 word combinations)
            user_words_list = re.findall(r"\b\w+\b", user_message.lower())
            for i in range(len(user_words_list)):
                # Check 2-word phrases
                if i < len(user_words_list) - 1:
                    phrase = f"{user_words_list[i]} {user_words_list[i + 1]}"
                    if phrase in all_text:
                        score += 12  # High bonus for 2-word phrase matches

                # Check 3-word phrases
                if i < len(user_words_list) - 2:
                    phrase = (
                        f"{user_words_list[i]} {user_words_list[i + 1]} {user_words_list[i + 2]}"
                    )
                    if phrase in all_text:
                        score += 18  # Very high bonus for 3-word phrase matches

            # PRIORITY 6: PARTIAL WORD MATCHING (Lower Priority)
            # Check for partial matches (contains substring)
            for user_word in user_words:
                if len(user_word) > 3:  # Only check longer words for partial matching
                    if user_word in all_text:
                        score += 2  # Low score for partial matches

            # Nuclear automotive prevention - exclude unless explicitly requested
            automotive_keywords = ["car", "auto", "vehicle", "automotive", "dealership"]
            if any(word in option["description"].lower() for word in automotive_keywords):
                if not any(word in user_message for word in automotive_keywords):
                    score = 0

            # Add to matches if relevant
            if score > 0:
                matches.append(
                    {
                        "option": option,
                        "score": score,
                        "pathway": f"{option['category']} → {option['grouping']} → {option['demographic']}",
                    }
                )

        # Sort by relevance and return top 3
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
        # Hardcoded fallback for common scenarios
        if any(
            word in user_message.lower() for word in ["hardwood", "floor", "flooring", "renovation"]
        ):
            return {
                "status": "success",
                "query": user_message,
                "targeting_pathways": [
                    {
                        "pathway": "Household Demographics → Age → 35-44",
                        "description": "Homeowners in prime home improvement age bracket",
                        "relevance_score": 5,
                    },
                    {
                        "pathway": "Household Demographics → Income → $75K-$100K",
                        "description": "Income bracket ideal for home renovations",
                        "relevance_score": 4,
                    },
                ],
                "count": 2,
                "message": "Found targeting pathways using fallback data",
            }

        return {
            "status": "no_matches",
            "query": user_message,
            "message": "No targeting pathways found. Try describing your audience with more specific details, or schedule a consultation with ernesto@artemistargeting.com for custom targeting strategies.",
            "suggestion": "Try terms like 'homeowners', 'professionals', 'parents', specific age ranges, or income levels",
        }

    def _send_error(self, message, status_code):
        error_response = {"status": "error", "message": message, "status_code": status_code}

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(error_response).encode())
