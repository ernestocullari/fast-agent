from http.server import BaseHTTPRequestHandler
import json
import os
import traceback
import re
import hashlib
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Global conversation state tracking
CONVERSATION_STATE = {}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Health check endpoint
        result = {
            "status": "✅ LIVE",
            "message": "Artemis Targeting MCP Server - ENHANCED WITH DESCRIPTIONS",
            "version": "4.1.0-CONFUSION-DETECTION-FIXED",
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

            print(f"🎯 RECEIVED MESSAGE: '{user_message}'")

            # **PRIORITY 1: Check for confusion/description requests FIRST**
            if self._detect_confusion_or_description_request(user_message.lower()):
                response = {
                    "status": "success",
                    "response": "I can see you'd like more clarity about these targeting options. Would you like me to include detailed descriptions for each pathway to help you understand what they mean and their accuracy?",
                    "targeting_pathways": [],
                    "conversation_action": "offer_descriptions",
                }
                print(f"🔍 RETURNING CONFUSION RESPONSE")
                self._send_json_response(response)
                return

            # **PRIORITY 2: Check for description confirmation**
            if self._detect_description_request(user_message.lower()):
                # Set description flag in conversation state
                conversation_key = self._create_conversation_key(user_message)
                conv_state = self._get_conversation_state(conversation_key)
                conv_state["show_descriptions"] = True

                response = {
                    "status": "success",
                    "response": "Perfect! I'll include detailed descriptions with your targeting pathways. What audience would you like to target?",
                    "targeting_pathways": [],
                    "conversation_action": "descriptions_enabled",
                }
                print(f"🔍 ENABLING DESCRIPTIONS")
                self._send_json_response(response)
                return

            # **PRIORITY 3: Now get targeting data for regular queries**
            targeting_data = self._get_targeting_data()
            if not targeting_data:
                self._send_error("Could not access targeting database", 500)
                return

            # Apply semantic phrase mapping
            processed_message = self._apply_semantic_mapping(user_message.lower())

            # Find matching targeting options with PROGRESSIVE PATHWAY LOGIC
            matches = self._find_targeting_matches_progressive(
                processed_message, targeting_data, user_message
            )

            if matches:
                response = self._format_targeting_response(matches, user_message)
            else:
                response = self._get_fallback_response(user_message)

            self._send_json_response(response)

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            self._send_error(f"Server error: {str(e)}", 500)

    def _send_json_response(self, response):
        """Helper to send JSON response"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def _detect_confusion_or_description_request(self, message_lower):
        """Detect if user is confused or wants descriptions"""
        confusion_indicators = [
            "what does this mean",
            "what is this",
            "i don't understand",
            "confused",
            "what are these",
            "explain",
            "what do these mean",
            "i don't know what",
            "unclear",
            "not sure what",
            "can you explain",
            "more details",
            "what does",
            "help me understand",
            "clarify",
            "accuracy",
            "accurate",
            "correct",
            "right",
            "wrong",
            "questionable",
            "make sense",
            "meaning",
            "don't get it",
            "what's this",
            "describe",
            "details about",
        ]

        # **DEBUG: Print what we're checking**
        print(f"🔍 CHECKING CONFUSION for: '{message_lower}'")

        for indicator in confusion_indicators:
            if indicator in message_lower:
                print(f"✅ CONFUSION DETECTED: Found '{indicator}' in message")
                return True

        print(f"❌ NO CONFUSION DETECTED")
        return False

    def _detect_description_request(self, message_lower):
        """Detect if user wants to see descriptions"""
        description_requests = [
            "yes",
            "show descriptions",
            "add descriptions",
            "with descriptions",
            "include descriptions",
            "see descriptions",
            "descriptions please",
            "more info",
            "more information",
            "details",
            "tell me more",
            "yes please",
            "sure",
            "okay",
            "ok",
            "that would help",
            "sounds good",
        ]

        # Check for simple affirmative responses
        simple_yes = message_lower.strip() in ["yes", "y", "sure", "ok", "okay", "yep", "yeah"]

        print(f"🔍 CHECKING DESCRIPTION REQUEST for: '{message_lower}'")

        if simple_yes:
            print(f"✅ DESCRIPTION REQUEST: Simple yes detected")
            return True

        for request in description_requests:
            if request in message_lower:
                print(f"✅ DESCRIPTION REQUEST: Found '{request}' in message")
                return True

        print(f"❌ NO DESCRIPTION REQUEST DETECTED")
        return False

    def _create_conversation_key(self, original_message):
        """Create a stable key for conversation tracking based on core intent"""

        # **CRITICAL FIX: Don't process confusion/description requests**
        message_lower = original_message.lower().strip()

        # If it's a confusion/description request, create simple key
        if self._detect_confusion_or_description_request(
            message_lower
        ) or self._detect_description_request(message_lower):
            print(f"🔑 CONVERSATION KEY: confusion_request (special handling)")
            return "confusion_request"

        # Remove "more options" noise and create key from core intent
        core_words = []
        noise_words = [
            "more",
            "additional",
            "other",
            "else",
            "different",
            "show",
            "give",
            "find",
            "me",
            "options",
            "pathways",
            "combinations",
            "great",
            "have",
            "any",
            "target",
            "targeting",
        ]

        words = re.findall(r"\b\w+\b", original_message.lower())
        for word in words:
            if word not in noise_words and len(word) > 2:
                core_words.append(word)

        # Create stable hash from core intent
        core_intent = " ".join(sorted(core_words))
        if not core_intent:  # Fallback for very short messages
            core_intent = original_message.lower().strip()

        key = hashlib.md5(core_intent.encode()).hexdigest()[:12]
        print(f"🔑 CONVERSATION KEY: {key} (from: '{core_intent}')")
        return key

    def _get_conversation_state(self, conversation_key):
        """Get or create conversation state"""
        global CONVERSATION_STATE

        if conversation_key not in CONVERSATION_STATE:
            CONVERSATION_STATE[conversation_key] = {
                "request_count": 0,
                "last_query": "",
                "show_descriptions": False,
                "creation_time": "now",
            }

        return CONVERSATION_STATE[conversation_key]

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
            "auto",
            "car",
            "cars",
            "vehicle",
            "vehicles",
            "automotive",
            "dealership",
            "truck",
            "trucks",
            "suv",
            "sedan",
            "honda",
            "toyota",
            "ford",
            "bmw",
            "mercedes",
            "audi",
            "lexus",
            "acura",
            "nissan",
            "mazda",
            "hyundai",
            "kia",
            "jeep",
            "ram",
            "chevrolet",
            "gmc",
            "cadillac",
            "buick",
            "volkswagen",
            "volvo",
            "subaru",
            "infiniti",
            "lincoln",
            "chrysler",
            "dodge",
            "mitsubishi",
            "porsche",
            "ferrari",
            "lamborghini",
            "maserati",
            "motorcycle",
            "motorcycles",
            "harley",
            "yamaha",
            "kawasaki",
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

    def _find_targeting_matches_progressive(self, user_message, targeting_data, original_message):
        """PROGRESSIVE PATHWAY MATCHING with ENHANCED single word 'more' detection"""

        # Create conversation key and get state
        conversation_key = self._create_conversation_key(original_message)
        conv_state = self._get_conversation_state(conversation_key)

        # Increment request count
        conv_state["request_count"] += 1
        conv_state["last_query"] = original_message

        request_number = conv_state["request_count"]

        print(f"🔄 CONVERSATION KEY: {conversation_key}")
        print(f"📊 REQUEST NUMBER: {request_number}")
        print(f"🔍 SHOW DESCRIPTIONS: {conv_state.get('show_descriptions', False)}")

        # ENHANCED FITNESS INTENT DETECTION
        fitness_keywords = [
            "gym",
            "fitness",
            "exercise",
            "workout",
            "health",
            "athletic",
            "sport",
            "wellness",
            "active",
        ]

        # ENHANCED "MORE OPTIONS" DETECTION - INCLUDES SINGLE WORD "MORE"
        more_options_phrases = [
            "more options",
            "more combinations",
            "more pathways",
            "additional",
            "other options",
            "what else",
            "any more",
            "show me more",
            "give me more",
            "different options",
            "alternative",
            "more",
            "else",
            "other",  # Single word triggers
        ]

        # SPECIAL: If message is very short (1-3 words) and contains "more", treat as more request
        is_short_more_request = (
            len(original_message.split()) <= 3 and "more" in original_message.lower()
        )

        # DETECT "MORE OPTIONS" REQUESTS
        is_more_request = (
            any(phrase in original_message.lower() for phrase in more_options_phrases)
            or is_short_more_request
        )

        if is_more_request:
            print(
                f"🔄 MORE REQUEST DETECTED: '{original_message}' (Short: {is_short_more_request})"
            )

        # SMART FITNESS INTENT LOGIC
        if is_more_request or request_number > 1:
            # If asking for "more options" or subsequent request, assume fitness intent
            has_fitness_intent = True
            print(f"🔄 SUBSEQUENT REQUEST #{request_number} - Assuming fitness intent")
        else:
            # Regular fitness detection for first request
            has_fitness_intent = any(
                keyword in original_message.lower() for keyword in fitness_keywords
            )
            print(f"🎯 INITIAL FITNESS INTENT DETECTED: {has_fitness_intent}")

        # Find ALL matches first
        all_matches = []
        user_words = set(re.findall(r"\b\w+\b", user_message.lower()))

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
                    "gyms & fitness clubs": 10000,
                    "gym - frequent visitor": 9500,
                    "fitness enthusiast": 9000,
                    "fitness moms": 8500,
                    "fitness dads": 8500,
                    "health & fitness": 8000,
                    "personal fitness & exercise": 7500,
                    "activewear": 7000,
                    "athletic shoe": 6500,
                    "sporting goods": 6000,
                    "gym membership": 5500,
                    "fitness device": 5000,
                    "interest in fitness": 4500,
                    "interest in sports": 4000,
                    "sports enthusiast": 3500,
                }

                for exact_match, points in exact_fitness_matches.items():
                    if exact_match in all_text:
                        score += points

                # PRIORITY 2: FITNESS CATEGORY BOOSTS (5,000+ points)
                fitness_categories = {
                    "purchase predictors": 5000,
                    "mobile location models": 4500,
                    "household behaviors & interests": 4000,
                    "lifestyle propensities": 3500,
                    "household demographics": 3000,
                }

                for fit_cat, points in fitness_categories.items():
                    if fit_cat in category_lower:
                        score += points

                # PRIORITY 3: FITNESS WORD MATCHING (1,000+ points each)
                for word in fitness_keywords:
                    if word in all_text:
                        score += 1000

            else:
                # NON-FITNESS QUERIES: Standard scoring
                demographic_words = set(re.findall(r"\b\w+\b", demographic_lower))
                exact_demo_matches = user_words.intersection(demographic_words)

                if exact_demo_matches:
                    match_percentage = (
                        len(exact_demo_matches) / len(user_words) if user_words else 0
                    )
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
                match_data = {
                    "option": option,
                    "score": score,
                    "pathway": f"{option['category']} → {option['grouping']} → {option['demographic']}",
                }

                # **NEW: Include description in match data for later use**
                match_data["description"] = option["description"]

                all_matches.append(match_data)

        # Sort all matches by score (highest first)
        all_matches.sort(key=lambda x: x["score"], reverse=True)

        # PROGRESSIVE PATHWAY SELECTION
        if request_number == 1:
            # First request: Return top 3 (positions 0-2)
            selected_matches = all_matches[0:3]
            range_text = "1-3"
        elif request_number == 2:
            # Second request: Return next 4 (positions 3-6)
            selected_matches = all_matches[3:7]
            range_text = "4-7"
        elif request_number == 3:
            # Third request: Return next 4 (positions 7-10)
            selected_matches = all_matches[7:11]
            range_text = "8-11"
        elif request_number == 4:
            # Fourth request: Return final 4 (positions 11-14)
            selected_matches = all_matches[11:15]
            range_text = "12-15"
        else:
            # Beyond 4 requests: No more options
            selected_matches = []
            range_text = "EXHAUSTED"

        print(f"🎯 RETURNING PATHWAYS {range_text}: {len(selected_matches)} matches")
        print(f"📊 TOTAL AVAILABLE: {len(all_matches)} matches")

        if selected_matches:
            scores = [m["score"] for m in selected_matches]
            print(f"🏆 SCORES FOR THIS BATCH: {scores}")

        return selected_matches

    def _format_targeting_response(self, matches, user_message):
        if not matches:
            return {
                "status": "no_more_matches",
                "query": user_message,
                "message": "You've seen all available targeting combinations for this audience. Try a different audience description or schedule a consultation with ernesto@artemistargeting.com for custom targeting strategies.",
                "targeting_pathways": [],
                "count": 0,
            }

        # Get conversation state to check if descriptions should be included
        conversation_key = self._create_conversation_key(user_message)
        conv_state = self._get_conversation_state(conversation_key)
        show_descriptions = conv_state.get("show_descriptions", False)

        pathways = []
        for match in matches:
            pathway_data = {
                "pathway": match["pathway"],
                "relevance_score": match["score"],
            }

            # **NEW: Include description only if user requested it**
            if show_descriptions:
                pathway_data["description"] = match.get("description", "No description available")

            pathways.append(pathway_data)

        response = {
            "status": "success",
            "query": user_message,
            "targeting_pathways": pathways,
            "count": len(pathways),
            "message": f"Found {len(pathways)} targeting pathway(s) for your audience",
        }

        # **NEW: Add flag to indicate if descriptions are included**
        if show_descriptions:
            response["includes_descriptions"] = True

        return response

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
