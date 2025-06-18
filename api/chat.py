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
            "message": "Artemis Targeting MCP Server - ENHANCED WITH COMBO-SPECIFIC CLARIFICATION & FIXED ENUMERATION",
            "version": "4.8.0-MORE-REQUEST-FIXED",
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

            # **PRIORITY 1: Check for specific combo clarification requests**
            combo_pattern = r"(?:combo|combination|option)\s*(\d+)"
            combo_match = re.search(combo_pattern, user_message.lower())

            if combo_match:
                combo_number = int(combo_match.group(1))
                conversation_key = self._create_conversation_key(user_message)
                conv_state = self._get_conversation_state(conversation_key)

                # Find the specific combo description
                delivered_pathways = conv_state.get("delivered_pathways", [])
                target_combo = None

                for pathway in delivered_pathways:
                    if pathway.get("combo_number") == combo_number:
                        target_combo = pathway
                        break

                if target_combo:
                    response = {
                        "status": "success",
                        "response": f"**Combo {combo_number} Description:**\n\n{target_combo['pathway']}\n\n*{target_combo.get('description', 'No description available')}*\n\nWould you like clarification on any other combos?",
                        "targeting_pathways": [],
                        "conversation_action": "specific_combo_clarification",
                    }
                    print(f"🔍 RETURNING SPECIFIC COMBO {combo_number} CLARIFICATION")
                    self._send_json_response(response)
                    return
                else:
                    response = {
                        "status": "success",
                        "response": f"I don't see a Combo {combo_number} in our conversation. Which specific combo would you like me to clarify?",
                        "targeting_pathways": [],
                        "conversation_action": "combo_not_found",
                    }
                    print(f"🔍 COMBO {combo_number} NOT FOUND")
                    self._send_json_response(response)
                    return

            # **PRIORITY 2: Check for general confusion/description requests**
            if self._detect_confusion_or_description_request(user_message.lower()):
                conversation_key = self._create_conversation_key(user_message)
                conv_state = self._get_conversation_state(conversation_key)
                delivered_pathways = conv_state.get("delivered_pathways", [])

                if delivered_pathways:
                    # User has seen combos, ask which ones they want clarified
                    combo_list = ", ".join(
                        [f"Combo {p['combo_number']}" for p in delivered_pathways]
                    )
                    response = {
                        "status": "success",
                        "response": f"I can provide detailed descriptions for any of the targeting pathways you've seen. Which combo would you like me to clarify?\n\nAvailable combos: {combo_list}\n\nJust say something like 'explain combo 1' or 'clarify combo 2'.",
                        "targeting_pathways": [],
                        "conversation_action": "ask_which_combo",
                    }
                else:
                    # No combos shown yet, general offer
                    response = {
                        "status": "success",
                        "response": "I can see you'd like more clarity about targeting options. Would you like me to include detailed descriptions with your targeting pathways?",
                        "targeting_pathways": [],
                        "conversation_action": "offer_descriptions",
                    }

                print(f"🔍 RETURNING CONFUSION RESPONSE")
                self._send_json_response(response)
                return

            # **PRIORITY 3: Check for description confirmation**
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
                print(f"🔍 ENABLING DESCRIPTIONS for key: {conversation_key}")
                self._send_json_response(response)
                return

            # **PRIORITY 4: Now get targeting data for regular queries**
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
            print(f"❌ TRACEBACK: {traceback.format_exc()}")
            self._send_error(f"Server error: {str(e)}", 500)

    def _send_json_response(self, response):
        """Helper to send JSON response"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def _detect_confusion_or_description_request(self, message_lower):
        """Detect if user is confused or wants descriptions for specific combos"""

        # Check for specific combo requests (e.g., "clarify combo 2", "explain combo 1")
        combo_pattern = r"(?:combo|combination|option)\s*(\d+)"
        combo_match = re.search(combo_pattern, message_lower)

        if combo_match:
            combo_number = int(combo_match.group(1))
            print(f"✅ SPECIFIC COMBO CLARIFICATION: Combo {combo_number}")
            return True

        confusion_indicators = [
            "what does this mean",
            "what is this",
            "i don't understand",
            "confused",
            "what are these",
            "explain",
            "what do these mean",
            "what does combo",
            "explain combo",
            "clarify combo",
            "describe combo",
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
            "tell me about",
            "more info about",
        ]

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

        # **CRITICAL FIX: Use single session key for all targeting-related conversations**
        message_lower = original_message.lower().strip()

        # For all targeting, confusion, and description requests - use same key
        targeting_indicators = [
            "target",
            "gym",
            "fitness",
            "health",
            "market",
            "hardwood",
            "floor",
            "what do these mean",
            "confused",
            "clarify",
            "explain",
            "combo",
            "combination",
            "yes",
            "no",
            "more",
        ]

        if any(indicator in message_lower for indicator in targeting_indicators):
            print(f"🔑 CONVERSATION KEY: targeting_session (unified session)")
            return "targeting_session"

        # For step completion and other non-targeting messages
        print(f"🔑 CONVERSATION KEY: general_session")
        return "general_session"

    def _get_conversation_state(self, conversation_key):
        """Get or create conversation state"""
        global CONVERSATION_STATE

        if conversation_key not in CONVERSATION_STATE:
            CONVERSATION_STATE[conversation_key] = {
                "request_count": 0,
                "last_query": "",
                "show_descriptions": False,
                "creation_time": "now",
                "original_intent": "",  # Track original user intent
                "delivered_pathways": [],  # Track delivered pathways with combo numbers
            }

        return CONVERSATION_STATE[conversation_key]

    def _apply_semantic_mapping(self, user_message):
        """Convert natural language phrases to targeting database terminology"""

        # ENHANCED semantic phrase mappings with home improvement support
        mappings = [
            # HOME IMPROVEMENT MAPPINGS
            (r"hardwood floors?", "hardwood flooring"),
            (r"wood floors?", "hardwood flooring"),
            (r"people in the market for hardwood floors?", "hardwood flooring shoppers"),
            (r"people looking for floors?", "flooring shoppers"),
            (r"home improvement", "home renovation"),
            (r"house renovation", "home renovation"),
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

            print(f"📊 LOADED {len(targeting_options)} targeting options from database")
            return targeting_options

        except Exception as e:
            print(f"❌ DATABASE ERROR: {str(e)}")
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
        """PROGRESSIVE PATHWAY MATCHING with FIXED enumeration and PROPER intent detection"""

        # Create conversation key and get state
        conversation_key = self._create_conversation_key(original_message)
        conv_state = self._get_conversation_state(conversation_key)

        # Store original intent on first request and RESET delivered pathways
        if conv_state["request_count"] == 0:
            conv_state["original_intent"] = original_message
            conv_state["delivered_pathways"] = []  # CRITICAL FIX: Reset on new conversation

        # Increment request count
        conv_state["request_count"] += 1
        conv_state["last_query"] = original_message

        request_number = conv_state["request_count"]

        print(f"🔄 CONVERSATION KEY: {conversation_key}")
        print(f"📊 REQUEST NUMBER: {request_number}")
        print(f"🎯 ORIGINAL INTENT: {conv_state['original_intent']}")
        print(f"🔍 SHOW DESCRIPTIONS: {conv_state.get('show_descriptions', False)}")
        print(f"📊 PREVIOUSLY DELIVERED: {len(conv_state.get('delivered_pathways', []))} combos")

        # ENHANCED INTENT DETECTION KEYWORDS
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

        home_improvement_keywords = [
            "floor",
            "floors",
            "flooring",
            "hardwood",
            "carpet",
            "tile",
            "renovation",
            "remodel",
            "home improvement",
            "house",
            "property",
            "real estate",
            "home",
            "renovation",
        ]

        # ENHANCED "MORE OPTIONS" DETECTION
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
            "other",
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

        # **CRITICAL FIX: SMART INTENT LOGIC - Use ORIGINAL intent, not assumed fitness**
        if is_more_request or request_number > 1:
            # Use ORIGINAL intent, not assumed fitness
            original_intent = conv_state.get("original_intent", "").lower()
            has_fitness_intent = any(keyword in original_intent for keyword in fitness_keywords)
            has_home_improvement_intent = any(
                keyword in original_intent for keyword in home_improvement_keywords
            )
            print(
                f"🔄 SUBSEQUENT REQUEST #{request_number} - Using original intent: '{original_intent}'"
            )
            print(f"🎯 FITNESS INTENT: {has_fitness_intent}")
            print(f"🏠 HOME IMPROVEMENT INTENT: {has_home_improvement_intent}")
        else:
            has_fitness_intent = any(
                keyword in original_message.lower() for keyword in fitness_keywords
            )
            has_home_improvement_intent = any(
                keyword in original_message.lower() for keyword in home_improvement_keywords
            )
            print(f"🎯 INITIAL FITNESS INTENT: {has_fitness_intent}")
            print(f"🏠 INITIAL HOME IMPROVEMENT INTENT: {has_home_improvement_intent}")

        # Find ALL matches first
        all_matches = []
        user_words = set(re.findall(r"\b\w+\b", user_message.lower()))

        for option in targeting_data:
            if self._is_automotive_related(option, original_message):
                continue

            score = 0
            category_lower = option["category"].lower()
            grouping_lower = option["grouping"].lower()
            demographic_lower = option["demographic"].lower()
            description_lower = option["description"].lower()
            all_text = f"{category_lower} {grouping_lower} {demographic_lower} {description_lower}"

            if has_fitness_intent:
                # FITNESS SCORING
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

                for word in fitness_keywords:
                    if word in all_text:
                        score += 1000

            elif has_home_improvement_intent:
                # HOME IMPROVEMENT SCORING
                exact_home_matches = {
                    "hardwood flooring": 10000,
                    "home improvement": 9500,
                    "renovation": 9000,
                    "flooring": 8500,
                    "home & garden": 8000,
                    "real estate": 7500,
                    "property": 7000,
                    "home renovation": 6500,
                    "house": 6000,
                }

                for exact_match, points in exact_home_matches.items():
                    if exact_match in all_text:
                        score += points

                home_categories = {
                    "home property": 8000,
                    "household behaviors & interests": 7000,
                    "purchase predictors": 6000,
                    "lifestyle propensities": 5000,
                    "household demographics": 4000,
                }

                for home_cat, points in home_categories.items():
                    if home_cat in category_lower:
                        score += points

                for word in home_improvement_keywords:
                    if word in all_text:
                        score += 1500

            else:
                # GENERAL DEMOGRAPHIC SCORING
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

                description_words = set(re.findall(r"\b\w+\b", description_lower))
                desc_matches = user_words.intersection(description_words)
                if desc_matches:
                    score += len(desc_matches) * 15

            if score > 0:
                match_data = {
                    "option": option,
                    "score": score,
                    "pathway": f"{option['category']} → {option['grouping']} → {option['demographic']}",
                    "description": option["description"],
                }
                all_matches.append(match_data)

        # Sort by score
        all_matches.sort(key=lambda x: x["score"], reverse=True)

        # **FIXED PROGRESSIVE PATHWAY SELECTION**
        if request_number == 1:
            selected_matches = all_matches[0:3]
            start_combo = 1
            range_text = "1-3"
        elif request_number == 2:
            selected_matches = all_matches[3:6]
            start_combo = 4
            range_text = "4-6"
        elif request_number == 3:
            selected_matches = all_matches[6:9]
            start_combo = 7
            range_text = "7-9"
        elif request_number == 4:
            selected_matches = all_matches[9:12]
            start_combo = 10
            range_text = "10-12"
        elif request_number == 5:
            selected_matches = all_matches[12:15]
            start_combo = 13
            range_text = "13-15"
        else:
            selected_matches = []
            start_combo = 0
            range_text = "EXHAUSTED"

        # **FIXED: Proper combo numbering without duplicates**
        for i, match in enumerate(selected_matches):
            combo_number = start_combo + i
            match["combo_number"] = combo_number

            # Store in conversation state (avoid duplicates)
            existing_combo = any(
                p.get("combo_number") == combo_number for p in conv_state["delivered_pathways"]
            )

            if not existing_combo:
                conv_state["delivered_pathways"].append(
                    {
                        "combo_number": combo_number,
                        "pathway": match["pathway"],
                        "description": match["description"],
                    }
                )

        print(f"🎯 RETURNING PATHWAYS {range_text}: {len(selected_matches)} matches")
        print(f"📊 TOTAL DELIVERED: {len(conv_state['delivered_pathways'])} combos")
        print(f"📊 TOTAL AVAILABLE: {len(all_matches)} matches")

        if selected_matches:
            combos = [m["combo_number"] for m in selected_matches]
            print(f"🔢 COMBO NUMBERS: {combos}")

        return selected_matches

    def _format_targeting_response(self, matches, user_message):
        """ENHANCED response formatting with n8n compatibility"""
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
        original_intent = conv_state.get("original_intent", "your audience")
        request_number = conv_state["request_count"]

        print(
            f"🔍 FORMATTING RESPONSE: show_descriptions={show_descriptions} for key={conversation_key}"
        )
        print(f"📊 REQUEST NUMBER: {request_number}")
        print(f"🎯 ORIGINAL INTENT: {original_intent}")

        pathways = []
        for match in matches:
            pathway_data = {
                "combo_number": match["combo_number"],
                "pathway": match["pathway"],
                "relevance_score": match["score"],
                "category": match["option"]["category"],
                "grouping": match["option"]["grouping"],
                "demographic": match["option"]["demographic"],
                "description": match.get("description", "No description available"),
            }
            pathways.append(pathway_data)

        # **CRITICAL FIX: Pass starting combo number to n8n**
        starting_combo = matches[0]["combo_number"] if matches else 1

        response = {
            "status": "success",
            "query": user_message,
            "targeting_pathways": pathways,
            "count": len(pathways),
            "original_intent": original_intent,
            "request_number": request_number,
            "starting_combo_number": starting_combo,
            "includes_descriptions": show_descriptions,
            "conversation_action": "targeting_results",
        }

        print(f"✅ FORMATTED RESPONSE: {len(pathways)} pathways, starting combo {starting_combo}")
        print(f"✅ RESPONSE STRUCTURE: {list(response.keys())}")
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
