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
            "message": "Artemis Targeting MCP Server - Exact Match Priority",
            "version": "1.2.0",
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

        # EXACT MATCH PRIORITY ALGORITHM
        for option in targeting_data:
            score = 0

            # TIER 1: PERFECT DEMOGRAPHIC MATCHES (Massive Priority)
            demographic_lower = option["demographic"].lower()

            # Check if ALL user words appear in the demographic field
            demographic_words = set(re.findall(r"\b\w+\b", demographic_lower))
            exact_demo_matches = user_words.intersection(demographic_words)

            if exact_demo_matches:
                # Calculate percentage of user words found in demographic
                match_percentage = len(exact_demo_matches) / len(user_words) if user_words else 0

                if match_percentage >= 0.8:  # 80%+ of user words found
                    score += 1000  # Massive score for near-perfect matches
                elif match_percentage >= 0.6:  # 60%+ of user words found
                    score += 500  # Very high score for good matches
                elif match_percentage >= 0.4:  # 40%+ of user words found
                    score += 250  # High score for decent matches
                else:
                    score += len(exact_demo_matches) * 50  # Standard scoring

            # TIER 2: EXACT PHRASE MATCHING in Demographic
            # Check for consecutive word phrases from user input
            user_words_list = re.findall(r"\b\w+\b", user_message.lower())

            # Check for exact phrases (2+ consecutive words)
            for i in range(len(user_words_list)):
                for j in range(i + 2, len(user_words_list) + 1):
                    phrase = " ".join(user_words_list[i:j])
                    if phrase in demographic_lower:
                        phrase_length = j - i
                        score += 200 * phrase_length  # Higher score for longer phrases

            # TIER 3: DESCRIPTION FIELD MATCHING (Medium Priority)
            description_lower = option["description"].lower()
            description_words = set(re.findall(r"\b\w+\b", description_lower))
            desc_matches = user_words.intersection(description_words)

            if desc_matches:
                score += len(desc_matches) * 15

                # Bonus for phrase matches in description
                for i in range(len(user_words_list)):
                    for j in range(i + 2, len(user_words_list) + 1):
                        phrase = " ".join(user_words_list[i:j])
                        if phrase in description_lower:
                            score += 25 * (j - i)

            # TIER 4: CATEGORY AND GROUPING MATCHING (Lower Priority)
            category_lower = option["category"].lower()
            grouping_lower = option["grouping"].lower()

            category_words = set(re.findall(r"\b\w+\b", category_lower))
            grouping_words = set(re.findall(r"\b\w+\b", grouping_lower))

            cat_matches = user_words.intersection(category_words)
            group_matches = user_words.intersection(grouping_words)

            if cat_matches:
                score += len(cat_matches) * 8
            if group_matches:
                score += len(group_matches) * 8

            # TIER 5: SUBSTRING MATCHING (Lowest Priority)
            # Only for words longer than 4 characters
            all_text = f"{demographic_lower} {description_lower} {category_lower} {grouping_lower}"
            for word in user_words:
                if len(word) > 4 and word in all_text:
                    score += 3

            # Nuclear automotive prevention
            automotive_keywords = ["car", "auto", "vehicle", "automotive", "dealership"]
            if any(word in description_lower for word in automotive_keywords):
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
