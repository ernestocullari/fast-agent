from http.server import BaseHTTPRequestHandler
import json
import os
import traceback
import re
import hashlib
import logging
from functools import lru_cache
from typing import Dict, List, Optional, Tuple
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Configure structured logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global conversation state tracking
CONVERSATION_STATE = {}


# CONFIGURATION: Intent Detection Keywords (Class-level constants)
class TargetingConfig:
    FITNESS_KEYWORDS = [
        "gym",
        "fitness",
        "exercise",
        "workout",
        "health",
        "athletic",
        "sport",
        "wellness",
        "active",
        "physical activity",
        "training",
    ]

    FOOD_KEYWORDS = [
        "food",
        "foodies",
        "restaurant",
        "restaurants",
        "dining",
        "dine",
        "eat",
        "meal",
        "cuisine",
        "chef",
        "cook",
        "culinary",
        "fast food",
        "family restaurant",
        "frequent diner",
    ]

    HOME_KEYWORDS = [
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
        "construction",
    ]

    MORE_OPTIONS_PHRASES = [
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

    # SCORING RULES: Configurable JSON-like structure
    SCORING_RULES = {
        "FITNESS": {
            "exact_matches": {
                "gyms & fitness clubs": 10000,
                "gym - frequent visitor": 9500,
                "fitness enthusiast": 9000,
                "health & fitness": 8000,
                "personal fitness & exercise": 7500,
                "fitness": 7000,
                "exercise": 6500,
                "workout": 6000,
                "athletic": 5500,
                "sport": 5000,
            },
            "category_weights": {
                "household behaviors & interests": 5000,
                "lifestyle propensities": 4000,
                "purchase predictors": 3500,
                "mobile location models": 3000,
                "consumer behavior": 2500,
            },
            "keyword_bonus": 1000,
            "max_score_cap": 15000,
        },
        "FOOD": {
            "exact_matches": {
                "family restaurant": 10000,
                "frequent diner": 9500,
                "fast food": 9000,
                "restaurant": 8500,
                "food": 8000,
                "dining": 7500,
                "culinary": 7000,
                "cuisine": 6500,
            },
            "category_weights": {
                "lifestyle models": 8000,
                "consumer behavior": 7000,
                "household behaviors & interests": 6000,
                "purchase predictors": 5000,
                "consumer financial insights": 4000,
            },
            "keyword_bonus": 1500,
            "max_score_cap": 15000,
        },
        "HOME": {
            "exact_matches": {
                "hardwood flooring": 10000,
                "home improvement": 9500,
                "renovation": 9000,
                "flooring": 8500,
                "real estate": 8000,
                "property": 7500,
                "home": 7000,
            },
            "category_weights": {
                "home property": 8000,
                "household behaviors & interests": 7000,
                "purchase predictors": 6000,
                "lifestyle propensities": 5000,
            },
            "keyword_bonus": 1500,
            "max_score_cap": 15000,
        },
        "GENERAL": {
            "exact_match_multiplier": 1000,
            "partial_match_multiplier": 250,
            "description_bonus": 15,
            "max_score_cap": 5000,
        },
    }

    # COMBO PAGING: Configurable window size
    COMBOS_PER_PAGE = 3
    MAX_PAGES = 5


class TargetingMatcher:
    """Optimized targeting matcher with caching and normalized scoring"""

    def __init__(self):
        self._match_cache = {}

    @lru_cache(maxsize=128)
    def _normalize_text(self, text: str) -> str:
        """Cache normalized text to avoid redundant processing"""
        if not text:
            return ""
        return re.sub(r"[^\w\s]", " ", str(text).lower()).strip()

    def _detect_intent(self, message: str) -> str:
        """Detect user intent based on keywords"""
        message_lower = self._normalize_text(message)

        if any(keyword in message_lower for keyword in TargetingConfig.FITNESS_KEYWORDS):
            return "FITNESS"
        elif any(keyword in message_lower for keyword in TargetingConfig.FOOD_KEYWORDS):
            return "FOOD"
        elif any(keyword in message_lower for keyword in TargetingConfig.HOME_KEYWORDS):
            return "HOME"
        else:
            return "GENERAL"

    def _calculate_normalized_score(self, option: Dict, intent: str, user_words: set) -> float:
        """Calculate normalized score with capping to prevent disproportionate stacking"""

        # Create cache key
        cache_key = f"{option['Category']}_{option['Demographic']}_{intent}"
        if cache_key in self._match_cache:
            return self._match_cache[cache_key]

        score = 0

        # Normalize all text once
        category_norm = self._normalize_text(option["category"])
        grouping_norm = self._normalize_text(option["grouping"])
        demographic_norm = self._normalize_text(option["demographic"])
        description_norm = self._normalize_text(option["description"])
        all_text = f"{category_norm} {grouping_norm} {demographic_norm} {description_norm}"

        scoring_rules = TargetingConfig.SCORING_RULES.get(
            intent, TargetingConfig.SCORING_RULES["GENERAL"]
        )

        if intent in ["FITNESS", "FOOD", "HOME"]:
            # Check exact matches
            exact_matches = scoring_rules.get("exact_matches", {})
            for match_text, points in exact_matches.items():
                if match_text in all_text:
                    score += points
                    break  # Only award highest exact match

            # Check category weights (capped)
            category_weights = scoring_rules.get("category_weights", {})
            for category, points in category_weights.items():
                if category in category_norm:
                    score += min(points, 5000)  # Cap category bonus
                    break

            # Keyword bonus (limited to prevent stacking)
            keyword_bonus = scoring_rules.get("keyword_bonus", 1000)
            keywords = getattr(TargetingConfig, f"{intent}_KEYWORDS")
            keyword_matches = sum(1 for keyword in keywords if keyword in all_text)
            score += min(keyword_matches * keyword_bonus, keyword_bonus * 2)  # Max 2x bonus

        else:  # GENERAL scoring
            demographic_words = set(re.findall(r"\b\w+\b", demographic_norm))
            exact_matches = user_words.intersection(demographic_words)

            if exact_matches:
                match_ratio = len(exact_matches) / len(user_words) if user_words else 0
                if match_ratio >= 0.8:
                    score += scoring_rules["exact_match_multiplier"]
                elif match_ratio >= 0.4:
                    score += scoring_rules["partial_match_multiplier"]

            # Description bonus
            description_words = set(re.findall(r"\b\w+\b", description_norm))
            desc_matches = user_words.intersection(description_words)
            score += len(desc_matches) * scoring_rules["description_bonus"]

        # Apply score cap
        max_cap = scoring_rules.get("max_score_cap", 10000)
        final_score = min(score, max_cap)

        # Cache result
        self._match_cache[cache_key] = final_score

        logger.debug(f"Scored {option['demographic']}: {final_score} (intent: {intent})")
        return final_score


# Global matcher instance
matcher = TargetingMatcher()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Health check endpoint
        result = {
            "status": "✅ LIVE",
            "message": "Artemis Targeting MCP Server - OPTIMIZED WITH CACHING & NORMALIZED SCORING",
            "version": "5.0.0-OPTIMIZED",
            "endpoints": ["GET /api/chat (health)", "POST /api/chat (targeting)"],
        }

        self._send_json_response(result)

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

            logger.info(f"Processing message: '{user_message}'")

            # **PRIORITY 1: Check for specific combo clarification requests**
            combo_pattern = r"(?:combo|combination|option)\s*(\d+)"
            combo_match = re.search(combo_pattern, user_message.lower())

            if combo_match:
                response = self._handle_combo_clarification(combo_match, user_message)
                self._send_json_response(response)
                return

            # **PRIORITY 2: Check for general confusion/description requests**
            if self._detect_confusion_or_description_request(user_message.lower()):
                response = self._handle_confusion_request(user_message)
                self._send_json_response(response)
                return

            # **PRIORITY 3: Check for description confirmation**
            if self._detect_description_request(user_message.lower()):
                response = self._handle_description_request(user_message)
                self._send_json_response(response)
                return

            # **PRIORITY 4: Handle targeting requests**
            targeting_data = self._get_targeting_data()
            if not targeting_data:
                self._send_error("Could not access targeting database", 500)
                return

            # Find targeting matches
            matches = self._find_targeting_matches_optimized(user_message, targeting_data)

            if matches:
                response = self._format_targeting_response(matches, user_message)
            else:
                response = self._get_fallback_response(user_message)

            self._send_json_response(response)

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            self._send_error(f"Server error: {str(e)}", 500)

    def _handle_combo_clarification(self, combo_match, user_message):
        """Handle specific combo clarification requests"""
        combo_number = int(combo_match.group(1))
        conversation_key = self._create_conversation_key(user_message)
        conv_state = self._get_conversation_state(conversation_key)

        delivered_pathways = conv_state.get("delivered_pathways", [])
        target_combo = next(
            (p for p in delivered_pathways if p.get("combo_number") == combo_number), None
        )

        if target_combo:
            logger.info(f"Returning clarification for combo {combo_number}")
            return {
                "status": "success",
                "response": f"**Combo {combo_number} Description:**\n\n{target_combo['pathway']}\n\n*{target_combo.get('description', 'No description available')}*\n\nWould you like clarification on any other combos?",
                "targeting_pathways": [],
                "conversation_action": "specific_combo_clarification",
            }
        else:
            return {
                "status": "success",
                "response": f"I don't see a Combo {combo_number} in our conversation. Which specific combo would you like me to clarify?",
                "targeting_pathways": [],
                "conversation_action": "combo_not_found",
            }

    def _handle_confusion_request(self, user_message):
        """Handle general confusion/description requests"""
        conversation_key = self._create_conversation_key(user_message)
        conv_state = self._get_conversation_state(conversation_key)
        delivered_pathways = conv_state.get("delivered_pathways", [])

        if delivered_pathways:
            combo_list = ", ".join([f"Combo {p['combo_number']}" for p in delivered_pathways])
            return {
                "status": "success",
                "response": f"I can provide detailed descriptions for any of the targeting pathways you've seen. Which combo would you like me to clarify?\n\nAvailable combos: {combo_list}\n\nJust say something like 'explain combo 1' or 'clarify combo 2'.",
                "targeting_pathways": [],
                "conversation_action": "ask_which_combo",
            }
        else:
            return {
                "status": "success",
                "response": "I can see you'd like more clarity about targeting options. Would you like me to include detailed descriptions with your targeting pathways?",
                "targeting_pathways": [],
                "conversation_action": "offer_descriptions",
            }

    def _handle_description_request(self, user_message):
        """Handle description confirmation requests"""
        conversation_key = self._create_conversation_key(user_message)
        conv_state = self._get_conversation_state(conversation_key)
        conv_state["show_descriptions"] = True

        logger.info(f"Enabled descriptions for conversation key: {conversation_key}")
        return {
            "status": "success",
            "response": "Perfect! I'll include detailed descriptions with your targeting pathways. What audience would you like to target?",
            "targeting_pathways": [],
            "conversation_action": "descriptions_enabled",
        }

    def _find_targeting_matches_optimized(
        self, user_message: str, targeting_data: List[Dict]
    ) -> List[Dict]:
        """OPTIMIZED targeting matcher with cleaner combo paging logic"""

        original_message = user_message
        conversation_key = self._create_conversation_key(original_message)
        conv_state = self._get_conversation_state(conversation_key)

        # Detect intent
        intent = matcher._detect_intent(user_message)

        # Check if this is a "more" request
        is_more_request = any(
            phrase in user_message.lower() for phrase in TargetingConfig.MORE_OPTIONS_PHRASES
        )
        is_short_more = len(user_message.split()) <= 3 and "more" in user_message.lower()

        # Detect new targeting request
        targeting_keywords = (
            TargetingConfig.FITNESS_KEYWORDS
            + TargetingConfig.FOOD_KEYWORDS
            + TargetingConfig.HOME_KEYWORDS
            + ["target", "find", "reach"]
        )
        is_new_targeting_request = (
            not (is_more_request or is_short_more)
            and any(keyword in user_message.lower() for keyword in targeting_keywords)
            and conv_state["request_count"] == 0
        )

        # Reset for new targeting conversations
        if is_new_targeting_request:
            logger.info("New targeting request detected - resetting state")
            conv_state["request_count"] = 0
            conv_state["delivered_pathways"] = []
            conv_state["original_intent"] = original_message

        # Store original intent on first request
        if conv_state["request_count"] == 0:
            conv_state["original_intent"] = original_message

        # Increment request count
        conv_state["request_count"] += 1
        request_number = conv_state["request_count"]

        # Use original intent for subsequent requests
        if request_number > 1:
            intent = matcher._detect_intent(conv_state.get("original_intent", ""))

        logger.info(f"Request #{request_number}, Intent: {intent}")

        # Find and score all matches
        all_matches = []
        user_words = set(re.findall(r"\b\w+\b", user_message.lower()))

        for option in targeting_data:
            if self._is_automotive_related(option, original_message):
                continue

            score = matcher._calculate_normalized_score(option, intent, user_words)

            if score > 0:
                match_data = {
                    "option": option,
                    "score": score,
                    "pathway": f"{option['Category']} → {option['Grouping']} → {option['Demographic']}",
                    "description": option["Description"],
                }
                all_matches.append(match_data)

        # Sort by score
        all_matches.sort(key=lambda x: x["score"], reverse=True)

        # **CLEANER COMBO PAGING LOGIC**
        combos_per_page = TargetingConfig.COMBOS_PER_PAGE
        start_index = (request_number - 1) * combos_per_page
        end_index = start_index + combos_per_page
        start_combo = start_index + 1

        selected_matches = all_matches[start_index:end_index]

        # Check if we've exceeded max pages
        if request_number > TargetingConfig.MAX_PAGES or not selected_matches:
            return []

        # Add combo numbers
        for i, match in enumerate(selected_matches):
            combo_number = start_combo + i
            match["combo_number"] = combo_number

            # Store in conversation state (avoid duplicates)
            if not any(
                p.get("combo_number") == combo_number for p in conv_state["delivered_pathways"]
            ):
                conv_state["delivered_pathways"].append(
                    {
                        "combo_number": combo_number,
                        "pathway": match["pathway"],
                        "description": match["description"],
                    }
                )

        range_text = f"{start_combo}-{start_combo + len(selected_matches) - 1}"
        logger.info(f"Returning pathways {range_text}: {len(selected_matches)} matches")

        return selected_matches

    def _detect_confusion_or_description_request(self, message_lower):
        """Detect confusion or description requests"""
        confusion_indicators = [
            "what does this mean",
            "what is this",
            "i don't understand",
            "confused",
            "what are these",
            "explain",
            "what do these mean",
            "clarify",
            "describe",
        ]
        return any(indicator in message_lower for indicator in confusion_indicators)

    def _detect_description_request(self, message_lower):
        """Detect description requests"""
        description_requests = [
            "yes",
            "show descriptions",
            "include descriptions",
            "more info",
            "details",
        ]
        simple_yes = message_lower.strip() in ["yes", "y", "sure", "ok", "okay"]
        return simple_yes or any(request in message_lower for request in description_requests)

    def _create_conversation_key(self, original_message):
        """Create conversation key for unified session tracking"""
        message_lower = original_message.lower().strip()
        targeting_indicators = [
            "target",
            "gym",
            "fitness",
            "food",
            "restaurant",
            "hardwood",
            "floor",
            "confused",
            "clarify",
            "explain",
            "combo",
            "yes",
            "no",
            "more",
        ]

        if any(indicator in message_lower for indicator in targeting_indicators):
            return "targeting_session"
        return "general_session"

    def _get_conversation_state(self, conversation_key):
        """Get or create conversation state"""
        global CONVERSATION_STATE

        if conversation_key not in CONVERSATION_STATE:
            CONVERSATION_STATE[conversation_key] = {
                "request_count": 0,
                "last_query": "",
                "show_descriptions": False,
                "original_intent": "",
                "delivered_pathways": [],
            }

        return CONVERSATION_STATE[conversation_key]

    @lru_cache(maxsize=1)
    def _get_targeting_data(self):
        """Cached targeting data retrieval"""
        try:
            private_key = os.getenv("GOOGLE_PRIVATE_KEY").replace("\\n", "\n")
            client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
            sheet_id = os.getenv("GOOGLE_SHEET_ID")

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

            service = build("sheets", "v4", credentials=credentials)

            # Try multiple range formats
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
            targeting_options = []
            start_row = 1 if values and "category" in str(values[0][0]).lower() else 0

            for row in values[start_row:]:
                if len(row) >= 4:
                    targeting_options.append(
                        {
                            "Category": row[0].strip(),
                            "Grouping": row[1].strip(),
                            "Demographic": row[2].strip(),
                            "Description": row[3].strip(),
                            "category": row[0].strip(),  # lowercase for compatibility
                            "grouping": row[1].strip(),
                            "demographic": row[2].strip(),
                            "description": row[3].strip(),
                        }
                    )

            logger.info(f"Loaded {len(targeting_options)} targeting options")
            return targeting_options

        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            return None

    def _is_automotive_related(self, option, user_message):
        """Enhanced automotive detection"""
        automotive_keywords = [
            "auto",
            "car",
            "cars",
            "vehicle",
            "automotive",
            "dealership",
            "truck",
            "honda",
            "toyota",
            "ford",
            "bmw",
            "mercedes",
            "audi",
            "lexus",
        ]

        # Don't filter if user wants automotive content
        if any(keyword in user_message.lower() for keyword in automotive_keywords):
            return False

        all_text = f"{option['Category']} {option['Grouping']} {option['Demographic']} {option['Description']}".lower()
        return any(keyword in all_text for keyword in automotive_keywords)

    def _format_targeting_response(self, matches, user_message):
        """Format response with proper structure for n8n"""
        if not matches:
            return {
                "status": "no_more_matches",
                "message": "You've seen all available targeting combinations for this audience. Try a different audience description or contact ernesto@artemistargeting.com for custom targeting strategies.",
                "targeting_pathways": [],
            }

        conversation_key = self._create_conversation_key(user_message)
        conv_state = self._get_conversation_state(conversation_key)

        pathways = []
        for match in matches:
            pathway_data = {
                "combo_number": match["combo_number"],
                "pathway": match["pathway"],
                "relevance_score": match["score"],
                "category": match["option"]["Category"],
                "grouping": match["option"]["Grouping"],
                "demographic": match["option"]["Demographic"],
                "description": match.get("description", "No description available"),
            }
            pathways.append(pathway_data)

        return {
            "status": "success",
            "targeting_pathways": pathways,
            "original_intent": conv_state.get("original_intent", user_message),
            "request_number": conv_state["request_count"],
            "starting_combo_number": matches[0]["combo_number"] if matches else 1,
            "includes_descriptions": conv_state.get("show_descriptions", False),
        }

    def _get_fallback_response(self, user_message):
        """Fallback response for no matches"""
        return {
            "status": "no_matches",
            "message": "No targeting pathways found. Try describing your audience with more specific details about fitness, food/dining, demographics, or interests.",
        }

    def _send_json_response(self, response):
        """Send JSON response with proper headers"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def _send_error(self, message, status_code):
        """Send error response"""
        error_response = {"status": "error", "message": message}
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(error_response).encode())
