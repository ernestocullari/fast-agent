# /workspaces/fast-agent/api/chat.py

import json
import os
import traceback
import re
import hashlib
import logging
import time
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

# Import Flask components
from flask import Flask, request, jsonify
from flask_cors import CORS  # For handling Cross-Origin Resource Sharing

# Import Google API components
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError  # CONFIRMED IMPORT

# --- Configure structured logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Global Conversation State (TEMPORARY - will be externalized for production) ---
# THIS DICTIONARY IS NOT PERSISTENT ACROSS SERVERLESS INVOCATIONS.
# IT WILL RESET ON COLD STARTS. FOR PRODUCTION, REPLACE WITH REDIS OR A DATABASE.
CONVERSATION_STATE_STORE = {}

# --- Global for Google Sheets Service and Data Cache ---
_sheets_service = None
_targeting_data_cache = None
_last_sheets_fetch_time = 0
SHEETS_CACHE_TTL = 3600  # Cache for 1 hour (adjust as needed)

# --- Initialize Flask Application ---
app = Flask(__name__)

# --- Configure CORS for your Flask app ---
# This is crucial for n8n to be able to make requests to your Vercel endpoint.
# In production, replace "*" with specific origins of your n8n instance if possible.
CORS(app, resources={r"/api/*": {"origins": "*"}})


# --- HEALTH CHECK ENDPOINT (GET request) ---
@app.route("/api/chat", methods=["GET"])
def health_check():
    """
    Handles GET requests for health checks.
    """
    result = {
        "status": "✅ LIVE",
        "message": "Artemis Targeting MCP Server - Flask Version",
        "version": "6.0.0-FLASK-ADAPTED",
        "endpoints": ["GET /api/chat (health)", "POST /api/chat (targeting)"],
    }
    return jsonify(result)


# --- MAIN CHAT/TARGETING ENDPOINT (POST request) ---
@app.route("/api/chat", methods=["POST"])
def process_chat_request():
    """
    Handles POST requests for targeting queries.
    """
    try:
        data = request.get_json()
        if not data:
            logger.error("Received empty or invalid JSON body.")
            return jsonify({"status": "error", "message": "Invalid JSON or empty body"}), 400

        user_message = data.get("message", "").strip()
        session_id = request.headers.get("X-N8N-Session-ID")

        if not user_message:
            logger.error("No message provided in the request.")
            return jsonify({"status": "error", "message": "No message provided"}), 400

        logger.info(f"Processing message: '{user_message}' with session_id: {session_id}")

        conversation_key = _create_conversation_key(user_message, session_id=session_id)
        logger.info(f"Determined conversation_key: {conversation_key}")

        combo_pattern = r"(?:combo|combination|option)\s*(\d+)"
        combo_match = re.search(combo_pattern, user_message.lower())

        if combo_match:
            response_data = _handle_combo_clarification(combo_match, user_message, conversation_key)
            return jsonify(response_data)

        if _detect_confusion_or_description_request(user_message.lower()):
            response_data = _handle_confusion_request(user_message, conversation_key)
            return jsonify(response_data)

        if _detect_description_request(user_message.lower()):
            response_data = _handle_description_request(user_message, conversation_key)
            return jsonify(response_data)

        targeting_data = _get_targeting_data_cached()
        if not targeting_data:
            logger.error("Failed to retrieve targeting data from Sheets (returned None).")
            return jsonify(
                {"status": "error", "message": "Could not access targeting database"}
            ), 500

        matches = _find_targeting_matches_optimized(user_message, targeting_data, conversation_key)

        if matches:
            response_data = _format_targeting_response(matches, user_message, conversation_key)
        else:
            response_data = _get_fallback_response(user_message)

        return jsonify(response_data)

    except json.JSONDecodeError:
        logger.error(f"JSON Decode Error for request: {request.data.decode()}")
        return jsonify({"status": "error", "message": "Invalid JSON format"}), 400
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Server error processing your request."}), 500


# --- CONFIGURATION: Intent Detection Keywords (Class-level constants) ---
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
    GAMING_KEYWORDS = [
        "video games",
        "gaming",
        "gamer",
        "video gamer",
        "play games",
        "gaming enthusiast",
        "console",
        "pc gaming",
        "esports",
        "online gaming",
        "mobile games",
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
        "GAMING": {
            "exact_matches": {
                "video gamer": 10000,
                "gaming": 9000,
                "video games": 8500,
                "gamer": 8000,
                "entertainment": 7000,
                "games": 6500,
            },
            "category_weights": {
                "lifestyle propensities": 8000,
                "household behaviors & interests": 7000,
                "consumer behavior": 6000,
                "entertainment": 5000,
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
        elif any(keyword in message_lower for keyword in TargetingConfig.GAMING_KEYWORDS):
            return "GAMING"
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

        if intent in ["FITNESS", "FOOD", "GAMING", "HOME"]:
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


# --- Google Sheets Data Retrieval Functions ---


def _get_sheets_service():
    """Initializes and returns a cached Google Sheets service."""
    global _sheets_service
    if _sheets_service is None:
        try:
            # READ PRIVATE KEY DIRECTLY FROM A LOCAL FILE (most robust for multi-line)
            # You must have 'service_account_key.pem' in your project root.
            # Make sure to ADD 'service_account_key.pem' to your .gitignore!
            try:
                with open("service_account_key.pem", "r") as f:
                    raw_private_key_content = f.read()
                logger.info("Private key content loaded from file 'service_account_key.pem'.")
                # --- NEW DIAGNOSTIC LINE ---
                logger.info(
                    f"DEBUG: Raw private key content (repr): {repr(raw_private_key_content)}"
                )
                # --- END NEW DIAGNOSTIC LINE ---
            except FileNotFoundError:
                logger.error("ERROR: service_account_key.pem not found. Cannot load private key.")
                _sheets_service = None
                return None
            except Exception as file_e:
                logger.error(
                    f"ERROR: Failed to read private key from file: {file_e}", exc_info=True
                )
                _sheets_service = None
                return None

            # --- NEW LOGIC: Reconstruct multi-line PEM from potentially single-line input ---
            # Remove existing BEGIN/END markers and any newlines (if present)
            private_key_body = raw_private_key_content.replace("-----BEGIN PRIVATE KEY-----", "")
            private_key_body = private_key_body.replace("-----END PRIVATE KEY-----", "")
            private_key_body = (
                private_key_body.replace("\\n", "").replace("\n", "").strip()
            )  # Remove both literal and actual newlines

            # Re-add newlines every 64 characters (standard for PEM Base64 blocks)
            reformatted_private_key = ""
            for i in range(0, len(private_key_body), 64):
                reformatted_private_key += private_key_body[i : i + 64] + "\n"

            # Reconstruct the full PEM private_key
            private_key = (
                "-----BEGIN PRIVATE KEY-----\n"
                + reformatted_private_key.strip()  # Use strip to remove potential trailing newline from loop
                + "\n-----END PRIVATE KEY-----\n"
            )
            logger.debug(f"Reformatted private key for PEM structure. Length: {len(private_key)}")
            # --- END NEW LOGIC ---

            client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
            # Ensure these are also environment variables in production
            creds_info = {
                "type": "service_account",
                "project_id": os.getenv("GOOGLE_PROJECT_ID", "quick-website-dev"),
                "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID", "key_id_placeholder"),
                "private_key": private_key,  # Use the reformatted private_key
                "client_email": client_email,
                "client_id": os.getenv("GOOGLE_CLIENT_ID", "client_id_placeholder"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            credentials = Credentials.from_service_account_info(
                creds_info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
            )
            _sheets_service = build("sheets", "v4", credentials=credentials)
            logger.info("Google Sheets service initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {str(e)}", exc_info=True)
            _sheets_service = None
    return _sheets_service


def _get_targeting_data_cached():
    """
    Retrieves targeting data from Google Sheets, utilizing a time-based cache.
    """
    global _targeting_data_cache, _last_sheets_fetch_time
    current_time = time.time()

    if _targeting_data_cache is None or (current_time - _last_sheets_fetch_time > SHEETS_CACHE_TTL):
        logger.info("Fetching targeting data from Google Sheets (cache miss/expired).")
        service = _get_sheets_service()
        if not service:
            logger.error("Sheets service not available, cannot fetch targeting data.")
            return None

        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not sheet_id:
            logger.error("GOOGLE_SHEET_ID environment variable not set.")
            return None

        # Try multiple range formats for robustness
        fetched_data = None
        for range_name in ["Sheet1!A:D", "A:D", "A1:D5000"]:
            try:
                result = (
                    service.spreadsheets()
                    .values()
                    .get(spreadsheetId=sheet_id, range=range_name)
                    .execute()
                )
                values = result.get("values", [])
                targeting_options = []
                # Heuristic to detect header row: check if first row contains 'category' (case-insensitive)
                start_row = (
                    1
                    if values and len(values[0]) >= 4 and "category" in str(values[0][0]).lower()
                    else 0
                )

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
                fetched_data = targeting_options
                break  # Break if successful
            except HttpError as http_error:  # <--- ADDED/CONFIRMED HttpError CATCH
                # This will give us detailed HTTP errors from Google API
                logger.error(
                    f"Google Sheets API HttpError for range {range_name}: "
                    f"Status: {http_error.resp.status} - Content: {http_error.content.decode()}",
                    exc_info=True,  # This prints the full traceback
                )
                continue  # Try next range
            except Exception as e:  # <--- GENERAL EXCEPTION CATCH
                # Catch other general exceptions during API call that are not HttpErrors
                logger.error(
                    f"General error fetching from Sheets range {range_name}: {e}", exc_info=True
                )
                continue  # Try next range

        if fetched_data is None:
            logger.error(
                "Could not fetch targeting data from any specified range after multiple attempts."
            )
            return None

        _targeting_data_cache = fetched_data
        _last_sheets_fetch_time = current_time
        logger.info(f"Loaded {len(_targeting_data_cache)} targeting options from Sheets.")

    return _targeting_data_cache


# --- Conversation State Logic (Still using temporary global dict, needs Redis for production!) ---


def _create_conversation_key(user_message: str, session_id: Optional[str] = None):
    """
    Creates a conversation key. PRIORITIZES session_id from client (e.g., n8n).
    If no session_id, falls back to message-based heuristic (less reliable for multi-user).
    """
    message_lower = user_message.lower().strip()

    # If a session ID is provided by the client (n8n), use it directly. THIS IS PREFERRED.
    if session_id:
        logger.debug(f"Using provided session_id: {session_id}")
        return session_id

    # --- Fallback logic if NO session_id is provided by the client ---
    # This part is inherently less robust for multiple concurrent users without a real session_id.
    # For production, ENSURE n8n passes a session_id.

    more_indicators = TargetingConfig.MORE_OPTIONS_PHRASES
    is_more_request = any(indicator in message_lower for indicator in more_indicators)

    clarification_indicators = [
        "clarify combo",
        "explain combo",
        "describe combo",
        "combo",
        "what do these mean",
        "what does this mean",
        "explain",
        "clarify",
        "confused",
        "what are these",
        "i don't understand",
    ]
    is_clarification = any(indicator in message_lower for indicator in clarification_indicators)

    new_request_indicators = [
        "target people who",
        "find people who",
        "reach people who",
        "i want to target",
        "target gym",
        "target foodies",
        "target video games",
        "target gamers",
        "target shoppers",
        "target car buyers",
        "target home",
        "target hardwood",
        "people who play",
        "people who buy",
        "people interested in",
    ]
    is_new_request = any(indicator in message_lower for indicator in new_request_indicators)

    # For "more" or "clarification" requests without an explicit session_id,
    # try to use the most recent key from our temporary store.
    if is_more_request or is_clarification:
        recent_sessions = []
        for key in CONVERSATION_STATE_STORE.keys():
            # Heuristic to find timestamped session keys (e.g., "type_session_timestamp")
            if "_session_" in key:
                try:
                    parts = key.split("_")
                    if len(parts) > 2 and parts[-1].isdigit():
                        timestamp = int(parts[-1])
                        recent_sessions.append((timestamp, key))
                except ValueError:
                    continue
        if recent_sessions:
            recent_sessions.sort(reverse=True)  # Most recent first
            most_recent_key = recent_sessions[0][1]
            logger.info(f"Fallback: Found recent session for '{message_lower}': {most_recent_key}")
            return most_recent_key
        logger.warning(
            f"Fallback: No recent session found for '{message_lower}', defaulting to new generic session."
        )

    # If it's clearly a new targeting request (and no session_id), generate a new time-based key
    if is_new_request:
        # Hash message to create a more consistent key for similar new requests
        message_hash = hashlib.md5(user_message.encode("utf-8")).hexdigest()[:8]
        # Include timestamp for uniqueness, especially for repeat new requests
        return f"msg_hash_{message_hash}_session_{int(time.time())}"
    else:
        # For other requests (like "yes", or simple phrases), use a generic key.
        # This will lead to state mixing if multiple users send simple "yes"
        # without a session ID. HIGHLIGHTS NEED FOR EXTERNAL SESSION ID.
        return "unified_generic_session"


def _get_conversation_state(conversation_key):
    """
    Get or create conversation state from the (temporary) global store.
    ***REMINDER: This global store is NOT persistent across serverless invocations.***
    ***It MUST be replaced by an external store like Redis for production.***
    """
    if conversation_key not in CONVERSATION_STATE_STORE:
        CONVERSATION_STATE_STORE[conversation_key] = {
            "request_count": 0,
            "last_query": "",
            "show_descriptions": False,
            "original_intent": "",
            "delivered_pathways": [],
        }
    return CONVERSATION_STATE_STORE[conversation_key]


def _handle_combo_clarification(combo_match, user_message, conversation_key):
    """Handle specific combo clarification requests"""
    combo_number = int(combo_match.group(1))
    conv_state = _get_conversation_state(conversation_key)

    logger.info(
        f"CLARIFICATION REQUEST: Looking for combo {combo_number} in session {conversation_key}"
    )
    logger.info(
        f"Available pathways: {[p.get('combo_number') for p in conv_state.get('delivered_pathways', [])]}"
    )

    delivered_pathways = conv_state.get("delivered_pathways", [])
    target_combo = next(
        (p for p in delivered_pathways if p.get("combo_number") == combo_number), None
    )

    if target_combo:
        logger.info(f"Found combo {combo_number} - returning clarification")
        return {
            "status": "success",
            "response": f"**Combo {combo_number} Description:**\n\n{target_combo['pathway']}\n\n*{target_combo.get('description', 'No description available')}*\n\nWould you like clarification on any other combos?",
            "targeting_pathways": [],
            "conversation_action": "specific_combo_clarification",
        }
    else:
        logger.warning(f"Combo {combo_number} not found in session {conversation_key}")
        return {
            "status": "success",
            "response": f"I don't see a Combo {combo_number} in our conversation. Which specific combo would you like me to clarify?",
            "targeting_pathways": [],
            "conversation_action": "combo_not_found",
        }


def _handle_confusion_request(user_message, conversation_key):
    """Handle general confusion/description requests"""
    conv_state = _get_conversation_state(conversation_key)
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


def _handle_description_request(user_message, conversation_key):
    """Handle description confirmation requests"""
    conv_state = _get_conversation_state(conversation_key)
    conv_state["show_descriptions"] = True
    # For a real persistent store, you would save conv_state back here (e.g., redis_client.set(conversation_key, json.dumps(conv_state)))

    logger.info(f"Enabled descriptions for conversation key: {conversation_key}")
    return {
        "status": "success",
        "response": "Perfect! I'll include detailed descriptions with your targeting pathways. What audience would you like to target?",
        "targeting_pathways": [],
        "conversation_action": "descriptions_enabled",
    }


def _find_targeting_matches_optimized(
    user_message: str, targeting_data: List[Dict], conversation_key: str
) -> List[Dict]:
    """OPTIMIZED targeting matcher with FIXED repeat detection logic"""

    original_message = user_message
    conv_state = _get_conversation_state(conversation_key)

    # Detect intent
    intent = matcher._detect_intent(user_message)

    # Check if this is a "more" request
    is_more_request = any(
        phrase in user_message.lower() for phrase in TargetingConfig.MORE_OPTIONS_PHRASES
    )
    is_short_more = len(user_message.split()) <= 3 and "more" in user_message.lower()

    # CRITICAL FIX: Detect genuinely NEW targeting requests
    new_request_indicators = [
        "target people who",
        "find people who",
        "reach people who",
        "i want to target",
        "target gym",
        "target foodies",
        "target video games",
        "target gamers",
        "target shoppers",
        "target car buyers",
        "target home",
        "target hardwood",
        "people who play",
        "people who buy",
        "people interested in",
    ]
    is_new_request = any(indicator in user_message.lower() for indicator in new_request_indicators)

    # FIXED LOGIC: Always treat targeting requests as NEW unless explicitly "more" or "clarification"
    # This logic assumes the 'conversation_key' being passed in is already correctly derived.
    if is_new_request and not (is_more_request or is_short_more):
        logger.info(
            f"NEW TARGETING REQUEST DETECTED: '{user_message}' - RESETTING STATE for key {conversation_key}"
        )
        # Reset current conversation state data in the store
        CONVERSATION_STATE_STORE[conversation_key] = {  # Directly modify the global placeholder
            "request_count": 0,
            "last_query": "",
            "show_descriptions": False,
            "original_intent": original_message,
            "delivered_pathways": [],
        }
        conv_state = CONVERSATION_STATE_STORE[conversation_key]  # Get the reset state
    elif is_more_request or is_short_more:
        logger.info(
            f"MORE REQUEST DETECTED: '{user_message}' - CONTINUING SEQUENCE for key {conversation_key}"
        )
    else:
        # For non-targeting requests (like "yes", "what is this"), don't reset state
        logger.info(
            f"NON-TARGETING REQUEST: '{user_message}' - MAINTAINING STATE for key {conversation_key}"
        )

    # Store original intent on first request (or if it's a new explicit targeting request)
    if conv_state["request_count"] == 0 or is_new_request:
        conv_state["original_intent"] = original_message

    # Only increment request count for targeting/more requests
    if is_new_request or is_more_request or is_short_more:
        conv_state["request_count"] += 1
        request_number = conv_state["request_count"]
    else:
        # For description confirmations, etc., don't increment
        request_number = max(conv_state["request_count"], 1)  # Ensure it's at least 1

    # Use original intent for subsequent "more" requests
    if request_number > 1 and conv_state.get("original_intent"):
        intent = matcher._detect_intent(conv_state.get("original_intent", ""))

    logger.info(f"Request #{request_number}, Intent: {intent}, Key: {conversation_key}")
    logger.info(f"Is New Request: {is_new_request}, Is More: {is_more_request or is_short_more}")

    # Find and score all matches
    all_matches = []
    user_words = set(re.findall(r"\b\w+\b", user_message.lower()))

    for option in targeting_data:
        if _is_automotive_related(option, original_message):
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

    # CLEANER COMBO PAGING LOGIC
    combos_per_page = TargetingConfig.COMBOS_PER_PAGE
    start_index = (request_number - 1) * combos_per_page
    end_index = start_index + combos_per_page
    start_combo = start_index + 1

    selected_matches = all_matches[start_index:end_index]

    # Check if we've exceeded max pages or no matches
    if request_number > TargetingConfig.MAX_PAGES or not selected_matches:
        # If no selected matches AND it's not the very first request,
        # it means we ran out of new combos.
        if request_number > 1:
            return []  # Signal no more matches
        else:
            # If it's the first request and no matches, it's a "no pathways found" scenario
            pass  # Let _format_targeting_response or _get_fallback_response handle it

    # Add combo numbers
    for i, match in enumerate(selected_matches):
        combo_number = start_combo + i
        match["combo_number"] = combo_number

        # Store in conversation state (avoid duplicates)
        if not any(p.get("combo_number") == combo_number for p in conv_state["delivered_pathways"]):
            conv_state["delivered_pathways"].append(
                {
                    "combo_number": combo_number,
                    "pathway": match["pathway"],
                    "description": match["description"],
                }
            )

    # For a real external store (like Redis), you would save the updated conv_state back here:
    # Example: redis_client.set(conversation_key, json.dumps(conv_state), ex=3600) # 1 hour expiry

    range_text = f"{start_combo}-{start_combo + len(selected_matches) - 1}"
    logger.info(f"Returning pathways {range_text}: {len(selected_matches)} matches")
    logger.info(
        f"Stored pathways for session {conversation_key}: {[p['combo_number'] for p in conv_state['delivered_pathways']]}"
    )

    return selected_matches


def _detect_confusion_or_description_request(message_lower):
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


def _detect_description_request(message_lower):
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


def _is_automotive_related(option: Dict, user_message: str):
    """Enhanced automotive detection logic."""
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
        "ev",
        "electric vehicle",
    ]

    # Don't filter out if user explicitly asked for automotive content
    if any(keyword in user_message.lower() for keyword in automotive_keywords):
        return False

    # Check if the option itself is automotive and user DID NOT ask for it
    all_text = f"{option['Category']} {option['Grouping']} {option['Demographic']} {option['Description']}".lower()
    return any(keyword in all_text for keyword in automotive_keywords)


def _format_targeting_response(matches: List[Dict], user_message: str, conversation_key: str):
    """Format response with proper structure for n8n"""
    conv_state = _get_conversation_state(conversation_key)

    if (
        not matches and conv_state["request_count"] > 1
    ):  # Only return no_more_matches if it's not the first query
        return {
            "status": "no_more_matches",
            "message": "You've seen all available targeting combinations for this audience. Try a different audience description or contact ernesto@artemistargeting.com for custom targeting strategies.",
            "targeting_pathways": [],
        }
    elif not matches:  # First query and no matches
        return _get_fallback_response(user_message)

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


def _get_fallback_response(user_message: str):
    """Fallback response for no matches on initial query."""
    return {
        "status": "no_matches",
        "message": "No targeting pathways found. Try describing your audience with more specific details about fitness, food/dining, demographics, or interests.",
    }


# --- Flask Development Server (for local testing, NOT used by Vercel in production) ---
if __name__ == "__main__":
    # Ensure environment variables are set for local testing
    # For example:
    # export GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
    # export GOOGLE_CLIENT_EMAIL="your-service-account@your-project.iam.gserviceaccount.com"
    # export GOOGLE_SHEET_ID="your_sheet_id_here"

    # You can set a default port, or use the one provided by Codespaces
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
