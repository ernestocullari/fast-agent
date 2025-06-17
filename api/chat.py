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
            "message": "Artemis Targeting MCP Server - FITNESS FOCUSED + MORE OPTIONS",
            "version": "2.1.0-FITNESS-MEMORY",
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

            # Apply semantic phrase mapping
            processed_message = self._apply_semantic_mapping(user_message.lower())

            # Find matching targeting options with FITNESS PRIORITY + MORE OPTIONS MEMORY
            matches = self._find_targeting_matches_fitness_focused(processed_message, targeting_data, user_message)

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

    def _apply_semantic_mapping(self, user_message):
        """Convert natural language phrases to targeting database terminology"""

        # FITNESS-FOCUSED semantic phrase mappings
        mappings = [
            # FITNESS PRIORITY MAPPINGS
            (r"people who go to (?:the )?gym", "gym members"),
            (r"go to (?:the )?gym", "gym members"),
            (r"gym goers?", "gym members"),
            (r"fitness center", "gym members"),
            (r"work out", "fitness enthusiasts"),
            (r"workout", "fitness enthusiasts"),
            (r"exercise", "fitness enthusiasts"),
            (r"athletic", "fitness enthusiasts"),
            (r"health conscious", "health conscious consumers"),
            (r"wellness", "wellness enthusiasts"),
            
            # Market/Shopping intent patterns
            (r"people in the market for (.+)", r"\1 shoppers"),
            (r"in the market for (.+)", r"\1 shoppers"),
            (r"looking to buy (.+)", r"\1 shoppers"),
            (r"buyers of (.+)", r"\1 shoppers"),
            (r"purchasing (.+)", r"\1 shoppers"),
            (r"shopping for (.+)", r"\1 shoppers"),
            
            # Interest/Enthusiasm patterns
            (r"people interested in (.+)", r"\1 enthusiasts"),
            (r"interested in (.+)", r"\1 enthusiasts"),
            (r"fans of (.+)", r"\1 enthusiasts"),
            (r"people who love (.+)", r"\1 enthusiasts"),
            (r"people passionate about (.+)", r"\1 enthusiasts"),
            
            # Demographic patterns
            (r"people who (.+)", r"\1"),
            (r"individuals who (.+)", r"\1"),
            (r"consumers who (.+)", r"\1"),
            (r"households that (.+)", r"\1"),
            
            # Activity patterns
            (r"people who do (.+)", r"\1"),
            (r"people who practice (.+)", r"\1"),
            (r"people who participate in (.+)", r"\1"),
            
            # Possession patterns
            (r"people who own (.+)", r"\1 owners"),
            (r"owners of (.+)", r"\1 owners"),
            (r"people who have (.+)", r"\1 owners"),
        ]

        processed = user_message

        # Apply each mapping
        for pattern, replacement in mappings:
            processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)

        # Clean up extra spaces
        processed = re.sub(r"\s+", " ", processed).strip()

        return processed

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

    def _is_automotive_related(self, option, user_message):
        """Enhanced automotive detection across all fields"""

        # Comprehensive automotive keywords
        automotive_keywords = [
            "auto", "car", "cars", "vehicle", "vehicles", "automotive", "dealership",
            "truck", "trucks", "suv", "sedan", "honda", "toyota", "ford", "bmw",
            "mercedes", "audi", "lexus", "acura", "nissan", "mazda", "hyundai",
            "kia", "jeep", "ram", "chevrolet", "gmc", "cadillac", "buick",
            "volkswagen", "volvo", "subaru", "infiniti", "lincoln", "chrysler",
            "dodge", "mitsubishi", "porsche", "ferrari", "lamborghini", "maserati",
            "motorcycle", "motorcycles", "harley", "yamaha", "kawasaki",
        ]

        # Check if user explicitly requested automotive content
        user_wants_auto = any(keyword in user_message.lower() for keyword in automotive_keywords)

        if user_wants_auto:
            return False  # Don't filter if user wants automotive content

        # Check all fields for automotive content
        all_text = f"{option['category']} {option['grouping']} {option['demographic']} {option['description']}".lower()

        # More aggressive automotive detection
        for keyword in automotive_keywords:
            if keyword in all_text:
                return True

        return False

    def _find_targeting_matches_fitness_focused(self, user_message, targeting_data, original_message):
        """FITNESS-FOCUSED matching with 10,000+ point priority + MORE OPTIONS MEMORY"""
        
        matches = []
        user_words = set(re.findall(r"\b\w+\b", user_message.lower()))
        
        # ENHANCED FITNESS INTENT DETECTION WITH MORE OPTIONS MEMORY
        fitness_keywords = ['gym', 'fitness', 'exercise', 'workout', 'health', 'athletic', 'sport', 'wellness', 'active']
        
        # DETECT "MORE OPTIONS" REQUESTS
        more_options_phrases = ['more options', 'more', 'additional', 'other options', 'what else', 'any more', 'show me more', 'give me more', 'different options', 'alternative']
        is_more_request = any(phrase in original_message.lower() for phrase in more_options_phrases)
        
        # SMART FITNESS INTENT LOGIC
        if is_more_request:
            # If asking for "more options", assume fitness intent (most common use case)
            has_fitness_intent = True
            print(f"🔄 MORE OPTIONS REQUEST - Assuming fitness intent for: {original_message}")
        else:
            # Regular fitness detection
            has_fitness_intent = any(keyword in original_message.lower() for keyword in fitness_keywords)
            print(f"🎯 FITNESS INTENT DETECTED: {has_fitness_intent} for query: {original_message}")

        for option in targeting_data:
            # NUCLEAR AUTOMOTIVE PREVENTION
            if self._is_automotive_related(option, original_message):
                continue

            score = 0
            
            # Get all text fields
            category_lower = option["category"].lower()
            grouping_lower = option["grouping"].lower()
            demographic_lower = option["demographic"].lower()
            description_lower = option["description"].lower()
            all_text = f"{category_lower} {grouping_lower} {demographic_lower} {description_lower}"

            if has_fitness_intent:
                # PRIORITY 1: EXACT FITNESS MATCHES (10,000+ points)
                exact_fitness_matches = {
                    'gyms & fitness clubs': 10000,
                    'gym - frequent visitor': 9500,
                    'fitness enthusiast': 9000,
                    'fitness moms': 8500,
                    'fitness dads': 8500,
                    'health & fitness': 8000,
                    'personal fitness & exercise': 7500,
                    'activewear': 7000,
                    'athletic shoe': 6500,
                    'sporting goods': 6000,
                    'gym membership': 5500,
                    'fitness device': 5000,
                    'interest in fitness': 4500,
                    'interest in sports': 4000,
                    'sports enthusiast': 3500,
                }
                
                for exact_match, points in exact_fitness_matches.items():
                    if exact_match in all_text:
                        score += points
                        print(f"🎯 EXACT FITNESS MATCH: {exact_match} (+{points} points)")

                # PRIORITY 2: FITNESS CATEGORY BOOSTS (5,000+ points)
                fitness_categories = {
                    'purchase predictors': 5000,
                    'mobile location models': 4500,
                    'household behaviors & interests': 4000,
                    'lifestyle propensities': 3500,
                    'household demographics': 3000,
                }
                
                for fit_cat, points in fitness_categories.items():
                    if fit_cat in category_lower:
                        score += points
                        print(f"🏋️ FITNESS CATEGORY: {fit_cat} (+{points} points)")

                # PRIORITY 3: FITNESS WORD MATCHING (1,000+ points each)
                for word in fitness_keywords:
                    if word in all_text:
                        score += 1000
                        print(f"💪 FITNESS WORD: {word} (+1000 points)")
                        
            else:
                # NON-FITNESS QUERIES: Standard low scoring
                user_words = set(re.findall(r"\b\w+\b", user_message.lower()))
                
                # Standard scoring for non-fitness
                demographic_words = set(re.findall(r"\b\w+\b", demographic_lower))
                exact_demo_matches = user_words.intersection(demographic_words)

                if exact_demo_matches:
                    match_percentage = len(exact_demo_matches) / len(user_words) if user_words else 0
                    if match_percentage >= 0.8:
                        score += 1000
                    elif match_percentage >= 0.6:
                        score += 500
                    elif match_percentage >= 0.4:
                        score += 250
                    else:
                        score += len(exact_demo_matches) * 50

                # Description matching
                description_words = set(re.findall(r"\b\w+\b", description_lower))
                desc_matches = user_words.intersection(description_words)
                if desc_matches:
                    score += len(desc_matches) * 15

            # Add to matches if relevant
            if score > 0:
                matches.append({
                    "option": option,
                    "score": score,
                    "pathway": f"{option['category']} → {option['grouping']} → {option['demographic']}",
                })
                
                if score > 1000:  # Log high-scoring matches
                    print(f"🏆 HIGH SCORE: {score} for {option['demographic']}")

        # Sort by relevance and return top 3
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        print(f"📊 Total matches found: {len(matches)}")
        if matches:
            print(f"🥇 Top 3 scores: {[m['score'] for m in matches[:3]]}")
        
        return matches[:3]

    def _format_targeting_response(self, matches, user_message):
        pathways = []
        for match in matches:
            pathways.append({
                "pathway": match["pathway"],
                "description": match["option"]["description"],
                "relevance_score": match["score"],
            })

        return {
            "status": "success",
            "query": user_message,
            "targeting_pathways": pathways,
            "count": len(pathways),
            "message": f"Found {len(pathways)} targeting pathway(s) for your audience",
        }

    def _get_fallback_response(self, user_message):
        return {
            "status": "no_matches",
            "query": user_message,
            "message": "No targeting pathways found. Try describing your audience with more specific details about fitness, health, demographics, or interests.",
            "suggestion": "Try terms like 'gym members', 'fitness enthusiasts', 'health conscious consumers', or specific demographics",
        }

    def _send_error(self, message, status_code):
        error_response = {"status": "error", "message": message, "status_code": status_code}

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(error_response).encode())
