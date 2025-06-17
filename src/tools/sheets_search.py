import os
import json
import time
import difflib
import hashlib
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Performance optimizations
SEARCH_CACHE = {}
CONVERSATION_STATE = {}  # New: Track conversation history
CACHE_SIZE_LIMIT = 100
TIMEOUT_SECONDS = 45

# Enhanced automotive bias prevention - ZERO tolerance for non-auto queries
AUTOMOTIVE_TERMS = [
    "acura",
    "audi",
    "bmw",
    "buick",
    "cadillac",
    "chevrolet",
    "chevy",
    "chrysler",
    "dodge",
    "ford",
    "gmc",
    "honda",
    "hyundai",
    "infiniti",
    "jaguar",
    "jeep",
    "kia",
    "lexus",
    "lincoln",
    "mazda",
    "mercedes",
    "benz",
    "mitsubishi",
    "nissan",
    "pontiac",
    "porsche",
    "ram",
    "subaru",
    "toyota",
    "volkswagen",
    "volvo",
    "car",
    "auto",
    "vehicle",
    "truck",
    "suv",
    "sedan",
    "coupe",
    "convertible",
    "dealership",
    "automotive",
    "motor",
    "engine",
    "transmission",
    "brake",
    "cars",
    "autos",
    "vehicles",
    "trucks",
    "suvs",
    "sedans",
    "coupes",
    "convertibles",
    "dealers",
    "dealerships",
    "motors",
    "engines",
    "transmissions",
    "brakes",
    "tesla",
    "ferrari",
    "lamborghini",
    "maserati",
    "bentley",
    "automobile",
    "automobiles",
    "auto parts",
    "car parts",
    "automotive parts",
    "auto service",
    "car service",
    "tire",
    "tires",
    "mechanic",
    "garage",
    "auto repair",
    "car repair",
    "automotive repair",
    "intender",
    "intenders",
]


def is_automotive_content(text):
    """Enhanced check if content is automotive-related with word boundaries"""
    if not text:
        return False
    text_lower = text.lower().strip()

    for term in AUTOMOTIVE_TERMS:
        if (
            f" {term} " in f" {text_lower} "
            or text_lower.startswith(f"{term} ")
            or text_lower.endswith(f" {term}")
            or term == text_lower
        ):
            return True
    return False


def is_automotive_query(query):
    """Check if user explicitly wants automotive content"""
    query_lower = query.lower()
    explicit_auto_terms = [
        "car",
        "auto",
        "vehicle",
        "truck",
        "suv",
        "sedan",
        "automotive",
        "bmw",
        "mercedes",
        "toyota",
        "honda",
        "ford",
        "chevrolet",
        "chevy",
        "nissan",
        "dealership",
        "dealer",
        "motor",
        "engine",
        "tesla",
        "audi",
    ]
    return any(term in query_lower for term in explicit_auto_terms)


def detect_more_options_request(query):
    """SMART detection of 'more options' requests using natural language patterns"""
    query_lower = query.lower().strip()

    # Primary indicators for "more options"
    more_indicators = [
        "more",
        "additional",
        "other",
        "else",
        "different",
        "another",
        "alternative",
        "what else",
        "show me",
        "give me",
        "find me",
        "any other",
        "something else",
    ]

    # Context indicators that confirm it's about targeting
    context_indicators = [
        "option",
        "combination",
        "targeting",
        "pathway",
        "choice",
        "suggestion",
        "alternative",
        "demographic",
        "audience",
        "segment",
        "group",
        "category",
    ]

    # Question patterns that indicate more options
    question_patterns = [
        "what else do you have",
        "what other",
        "show me more",
        "give me more",
        "any other",
        "more options",
        "additional options",
        "other combinations",
        "different targeting",
        "something else",
        "alternatives",
    ]

    # Check for direct question patterns first
    for pattern in question_patterns:
        if pattern in query_lower:
            return True

    # Check for indicator combinations
    has_more_indicator = any(indicator in query_lower for indicator in more_indicators)
    has_context_indicator = any(context in query_lower for context in context_indicators)

    return has_more_indicator and has_context_indicator


def create_session_key(query):
    """Create a session key based on core query terms (ignoring 'more' indicators)"""
    # Remove common more-options words to get core intent
    stop_words = [
        "more",
        "additional",
        "other",
        "else",
        "different",
        "another",
        "alternative",
        "what",
        "show",
        "give",
        "find",
        "me",
        "options",
        "combinations",
        "targeting",
    ]

    # Extract core terms
    words = query.lower().split()
    core_words = [word for word in words if word not in stop_words and len(word) > 2]

    # Create consistent key from core terms
    core_query = " ".join(sorted(core_words))
    return hashlib.md5(core_query.encode()).hexdigest()[:16]


def calculate_enhanced_similarity(query_text, row_data):
    """SUPERCHARGED version with maximum fitness targeting power"""

    category = str(row_data.get("Category", "")).strip().lower()
    grouping = str(row_data.get("Grouping", "")).strip().lower()
    demographic = str(row_data.get("Demographic", "")).strip().lower()
    description = str(row_data.get("Description", "")).strip().lower()

    combined_text = f"{category} {grouping} {demographic} {description}"
    query_lower = query_text.lower().strip()

    # BULLETPROOF automotive blocking
    wants_auto = is_automotive_query(query_text)
    if not wants_auto:
        auto_indicators = [
            "auto",
            "car",
            "vehicle",
            "automotive",
            "bmw",
            "acura",
            "toyota",
            "honda",
            "ford",
            "chevrolet",
            "nissan",
            "mercedes",
            "audi",
            "lexus",
            "dealership",
            "dealer",
            "motor",
            "engine",
            "intender",
            "intenders",
        ]
        for auto_term in auto_indicators:
            if auto_term in combined_text:
                return 0.0  # IMMEDIATE REJECTION

    score = 0.0

    # SUPERCHARGED SEMANTIC MAPPINGS - Maximum fitness emphasis
    enhanced_mappings = {
        # FITNESS - ULTIMATE targeting power
        "fitness": [
            "purchase predictors",  # Gyms & Fitness Clubs - SUPREME PRIORITY
            "household behaviors & interests",  # Health & Fitness, Sports & Recreation
            "lifestyle propensities",  # Fitness Enthusiast
            "household indicators",  # Interest in fitness
            "household demographics",  # Fitness Moms/Dads
        ],
        "gym": [
            "purchase predictors",  # Gyms & Fitness Clubs - MAXIMUM PRIORITY
            "household behaviors & interests",  # Sports & Recreation → Personal Fitness
            "lifestyle propensities",  # Fitness Enthusiast
        ],
        "gyms": [
            "purchase predictors",  # Gyms & Fitness Clubs
            "household behaviors & interests",
            "lifestyle propensities",
        ],
        "enthusiasts": [
            "lifestyle propensities",  # Activity & Interests, Fitness Enthusiast
            "household behaviors & interests",
            "purchase predictors",
        ],
        "exercise": [
            "household behaviors & interests",  # Sports & Recreation → Personal Fitness
            "lifestyle propensities",  # Fitness Enthusiast
            "purchase predictors",  # Gyms & Fitness Clubs
        ],
        "workout": [
            "purchase predictors",  # Gyms & Fitness Clubs
            "household behaviors & interests",  # Sports & Recreation
            "lifestyle propensities",
        ],
        "supplements": [
            "purchase predictors",  # Health/supplement stores
            "household behaviors & interests",  # Health & Natural Foods
            "lifestyle propensities",
        ],
        # Health & Wellness - AMPLIFIED
        "health": [
            "household behaviors & interests",  # Main health category
            "purchase predictors",  # Health-related stores
            "household indicators",  # Contains health interests
            "lifestyle propensities",  # Fitness enthusiast
            "consumer behavior",  # Healthcare workers
        ],
        "wellness": [
            "household behaviors & interests",  # Health & fitness grouping
            "lifestyle propensities",  # Wellness activities
            "household indicators",  # Healthy living interest
            "lifestyle models",  # Consumer mentality
        ],
        "organic": [
            "consumer models",  # Consumer Personalities → Organic and natural
            "purchase predictors",  # Retail Shoppers → Organic Grocery
            "household behaviors & interests",  # Health & Natural Foods
        ],
        "natural": [
            "consumer models",  # Consumer Personalities → Organic and natural
            "household behaviors & interests",  # Health & Natural Foods, Natural Health Remedies
        ],
        # Mental wellness & mindfulness
        "mental": [
            "household behaviors & interests",  # Reading → Medical/Health
            "lifestyle models",  # Consumer Mentality categories
        ],
        "mindfulness": [
            "household behaviors & interests",  # Social Causes → Health
            "lifestyle models",  # Consumer Mentality
        ],
        "yoga": [
            "household behaviors & interests",  # Sports & Recreation
            "lifestyle propensities",  # Activity & Interests
        ],
        "meditation": [
            "household behaviors & interests",  # Social Causes → Health
            "lifestyle models",  # Consumer Mentality
        ],
        # Financial
        "financial": [
            "consumer financial insights",
            "financial",
        ],
        "investment": [
            "consumer financial insights",
            "financial",
        ],
        "wealth": [
            "consumer financial insights",
            "financial",
        ],
        # Shopping & Retail
        "shopping": [
            "purchase predictors",
            "household behaviors & interests",
            "online behavior models",
        ],
        "retail": [
            "purchase predictors",
            "household behaviors & interests",
        ],
        # Home & Property
        "home": [
            "home property",
            "mortgage/home purchase",
        ],
        "improvement": [
            "home property",
            "household behaviors & interests",
        ],
        "renovation": [
            "home property",
            "mortgage/home purchase",
        ],
    }

    # PRIORITY 1: MAXIMUM BOOSTED category matching for fitness
    query_words = query_lower.split()
    for word in query_words:
        if word in enhanced_mappings:
            target_categories = enhanced_mappings[word]
            for target_cat in target_categories:
                if target_cat in category:
                    # SUPREME BOOST for fitness-related terms
                    if word in ["fitness", "gym", "gyms", "exercise", "workout", "enthusiasts"]:
                        score += 500.0  # ULTIMATE fitness boost
                    else:
                        score += 200.0  # Enhanced category match
                    break

    # PRIORITY 2: Grouping and demographic matching with MASSIVE fitness boost
    for word in query_words:
        if len(word) > 3:
            # ULTIMATE BOOST for fitness in grouping/demographic
            fitness_terms = ["fitness", "gym", "exercise", "workout", "health"]
            if any(fitness_term in grouping for fitness_term in fitness_terms):
                score += 400.0  # Massive fitness grouping boost
            elif any(fitness_term in demographic for fitness_term in fitness_terms):
                score += 350.0  # Huge fitness demographic boost
            elif word in grouping:
                score += 150.0
            elif word in demographic:
                score += 120.0

    # PRIORITY 3: Description matching with fitness emphasis
    for word in query_words:
        if len(word) > 3:
            if word in description:
                # Extra boost for fitness-related descriptions
                if any(
                    fit_word in description
                    for fit_word in ["gym", "fitness", "exercise", "workout"]
                ):
                    score += 200.0  # Massive fitness description boost
                else:
                    score += 75.0

    # PRIORITY 4: Direct text matching
    if query_lower in combined_text:
        score += 50.0

    # PRIORITY 5: Individual word matching with fitness boost
    for word in query_words:
        if len(word) > 3:
            if word in combined_text:
                if word in ["fitness", "gym", "gyms", "exercise", "workout"]:
                    score += 40.0  # Big fitness word boost
                else:
                    score += 15.0

    # ULTIMATE CATEGORY DIVERSITY BOOSTING
    if "household demographics" in category:
        score *= 0.2  # MASSIVE reduction for household demographics (80% cut)
    elif "purchase predictors" in category:
        score *= 2.5  # ULTIMATE boost for purchase predictors (has gym data)
    elif "household behaviors & interests" in category:
        score *= 2.2  # MAJOR boost for behaviors & interests
    elif "lifestyle propensities" in category:
        score *= 2.0  # BIG boost for lifestyle propensities
    elif "consumer models" in category:
        score *= 1.8  # Good boost for consumer models

    return score


def search_in_data(query, sheets_data):
    """Search through sheets data with BULLETPROOF automotive filtering"""

    all_matches = []
    wants_auto = is_automotive_query(query)

    # Process up to 1500 rows for maximum coverage
    max_rows = min(len(sheets_data), 1500)

    for row in sheets_data[:max_rows]:
        # FIRST FILTER: Check each field individually for automotive content
        category = str(row.get("Category", "")).strip()
        grouping = str(row.get("Grouping", "")).strip()
        demographic = str(row.get("Demographic", "")).strip()
        description = str(row.get("Description", "")).strip()

        # SECOND FILTER: Check combined text
        all_text = f"{category} {grouping} {demographic} {description}"

        # BULLETPROOF CHECK: Skip if any automotive content found and not requested
        if not wants_auto:
            if (
                is_automotive_content(category)
                or is_automotive_content(grouping)
                or is_automotive_content(demographic)
                or is_automotive_content(description)
                or is_automotive_content(all_text)
            ):
                continue

        # Calculate similarity score (includes additional automotive check)
        similarity_score = calculate_enhanced_similarity(query, row)

        # Only include results with positive scores
        if similarity_score > 0.1:
            all_matches.append(
                {"row": row, "score": similarity_score, "similarity": similarity_score}
            )

    # Sort by score (highest first)
    all_matches.sort(key=lambda x: x["score"], reverse=True)

    # ENHANCED FILTER: Remove duplicates and ensure category diversity
    final_matches = []
    seen_pathways = set()
    category_counts = {}

    for match in all_matches:
        row = match["row"]
        category = row.get("Category", "")

        # Create pathway identifier
        pathway = f"{category} → {row.get('Grouping', '')} → {row.get('Demographic', '')}"

        if pathway in seen_pathways:
            continue

        # FINAL automotive check on pathway - BULLETPROOF
        if not wants_auto and is_automotive_content(pathway.lower()):
            continue

        # ENHANCED: Allow more entries for high-value categories
        category_count = category_counts.get(category, 0)
        # Allow up to 6 entries for Purchase Predictors, 3 for others
        max_per_category = 6 if "purchase predictors" in category.lower() else 3
        if category_count >= max_per_category:
            continue

        final_matches.append(match)
        seen_pathways.add(pathway)
        category_counts[category] = category_count + 1

        # Stop at 25 total matches for excellent selection
        if len(final_matches) >= 25:
            break

    return final_matches


def format_response_smart(matches, query, session_key, is_more_request=False):
    """SMART response formatting with intelligent more options handling"""

    if not matches:
        # Provide helpful suggestions based on query type
        query_lower = query.lower()
        suggestions = []

        if any(
            word in query_lower
            for word in [
                "home",
                "house",
                "improvement",
                "renovation",
                "hardware",
                "flooring",
                "hardwood",
                "kitchen",
                "bathroom",
            ]
        ):
            suggestions = [
                "home improvement shoppers",
                "hardware store visitors",
                "home renovation intenders",
                "flooring shoppers",
            ]
        elif any(
            word in query_lower
            for word in ["health", "fitness", "gym", "wellness", "nutrition", "exercise"]
        ):
            suggestions = [
                "health conscious consumers",
                "fitness enthusiasts",
                "wellness shoppers",
                "gym members",
            ]
        elif any(
            word in query_lower
            for word in ["fashion", "shopping", "retail", "clothing", "style", "beauty"]
        ):
            suggestions = [
                "fashion shoppers",
                "retail enthusiasts",
                "luxury shoppers",
                "brand conscious consumers",
            ]
        elif any(
            word in query_lower for word in ["travel", "hotel", "vacation", "tourism", "leisure"]
        ):
            suggestions = [
                "hotel guests",
                "business travelers",
                "vacation planners",
                "luxury travel shoppers",
            ]
        elif any(word in query_lower for word in ["food", "restaurant", "dining", "coffee"]):
            suggestions = [
                "restaurant visitors",
                "fine dining enthusiasts",
                "coffee shop customers",
                "food enthusiasts",
            ]
        elif any(
            word in query_lower
            for word in ["finance", "financial", "investment", "wealth", "money"]
        ):
            suggestions = [
                "financial services users",
                "investment shoppers",
                "wealth management clients",
                "premium banking customers",
            ]
        else:
            suggestions = [
                "high income households",
                "affluent professionals",
                "premium shoppers",
                "luxury consumers",
            ]

        suggestion_text = ", ".join(suggestions[:3])

        return {
            "success": False,
            "response": f"""I couldn't find strong matches in our targeting database for '{query}'.

Try being more specific with terms like:
- {suggestion_text}
- Include demographics (age, income, lifestyle) 
- Mention specific interests and behaviors

You can also explore our targeting tool or schedule a consultation with ernesto@artemistargeting.com for personalized assistance.""",
            "pathways": [],
            "query": query,
        }

    # INTELLIGENT RESULT SELECTION based on conversation state
    global CONVERSATION_STATE

    if session_key not in CONVERSATION_STATE:
        CONVERSATION_STATE[session_key] = {
            "shown_pathways": set(),
            "request_count": 0,
            "last_query_time": time.time(),
        }

    session_data = CONVERSATION_STATE[session_key]
    session_data["request_count"] += 1
    session_data["last_query_time"] = time.time()

    # Filter out previously shown pathways
    available_matches = []
    for match in matches:
        row = match["row"]
        pathway = (
            f"{row.get('Category', '')} → {row.get('Grouping', '')} → {row.get('Demographic', '')}"
        )
        if pathway not in session_data["shown_pathways"]:
            available_matches.append(match)

    # If we've run out of new matches, reset and use all matches
    if len(available_matches) < 3 and len(matches) >= 3:
        session_data["shown_pathways"].clear()
        available_matches = matches

    # Select 3 new pathways
    selected_matches = available_matches[:3]

    # Track what we're showing
    for match in selected_matches:
        row = match["row"]
        pathway = (
            f"{row.get('Category', '')} → {row.get('Grouping', '')} → {row.get('Demographic', '')}"
        )
        session_data["shown_pathways"].add(pathway)

    # Build response with strict taxonomic format
    pathways = []
    for match in selected_matches:
        row = match["row"]
        # STRICT FORMAT: Category → Grouping → Demographic
        category = str(row.get("Category", "")).strip()
        grouping = str(row.get("Grouping", "")).strip()
        demographic = str(row.get("Demographic", "")).strip()
        description = str(row.get("Description", "")).strip()

        pathway = f"{category} → {grouping} → {demographic}"
        pathways.append(
            {
                "pathway": pathway,
                "description": description[:150] + "..." if len(description) > 150 else description,
            }
        )

    # Format response text
    if is_more_request:
        response_parts = ["Here are additional targeting pathways for your audience:\n"]
    else:
        response_parts = ["Based on your audience description, here are the targeting pathways:\n"]

    for i, pathway_data in enumerate(pathways, 1):
        response_parts.append(f"**{i}.** {pathway_data['pathway']}")
        if pathway_data["description"]:
            response_parts.append(f"   _{pathway_data['description']}_\n")

    # Add "more options" info if available
    remaining_new = len(available_matches) - len(selected_matches)
    if remaining_new > 0:
        response_parts.append(
            f"**Additional Options Available:** {remaining_new} more targeting combinations"
        )
        response_parts.append("Ask for 'more targeting options' to see additional pathways.")

    response_parts.append(
        "\nThese pathways work together to effectively reach your target audience."
    )

    return {
        "success": True,
        "response": "\n".join(response_parts),
        "pathways": [p["pathway"] for p in pathways],
        "total_available": len(matches),
        "query": query,
        "is_more_request": is_more_request,
        "session_info": {
            "request_count": session_data["request_count"],
            "shown_count": len(session_data["shown_pathways"]),
        },
    }


class SheetsSearcher:
    def __init__(self):
        self.service = None
        self.sheet_id = None
        self.sheets_data_cache = None
        self.cache_timestamp = None
        self._setup_sheets_api()

    def _setup_sheets_api(self):
        """Initialize Google Sheets API"""
        try:
            client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
            private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
            self.sheet_id = os.getenv("GOOGLE_SHEET_ID")

            if not all([client_email, private_key, self.sheet_id]):
                raise ValueError("Missing required Google Sheets credentials")

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

            self.service = build("sheets", "v4", credentials=credentials)

        except Exception as e:
            print(f"Error setting up Google Sheets API: {e}")
            raise

    def _get_sheets_data(self):
        """Get and cache sheets data with rate limiting"""
        current_time = time.time()

        # EXTENDED CACHE: Keep data for 30 minutes
        if (
            self.sheets_data_cache
            and self.cache_timestamp
            and current_time - self.cache_timestamp < 1800
        ):  # 30 minutes
            return self.sheets_data_cache

        try:
            # ADD RATE LIMITING: Wait 2 seconds between API calls
            time.sleep(2)

            sheet = self.service.spreadsheets()
            result = sheet.values().get(spreadsheetId=self.sheet_id, range="A:D").execute()

            values = result.get("values", [])
            if not values:
                return []

            headers = values[0]
            data_rows = values[1:]

            try:
                category_idx = headers.index("Category")
                grouping_idx = headers.index("Grouping")
                demographic_idx = headers.index("Demographic")
                description_idx = headers.index("Description")
            except ValueError as e:
                return []

            sheets_data = []
            for row in data_rows:
                if len(row) > max(category_idx, grouping_idx, demographic_idx, description_idx):
                    row_dict = {
                        "Category": str(row[category_idx]).strip()
                        if len(row) > category_idx
                        else "",
                        "Grouping": str(row[grouping_idx]).strip()
                        if len(row) > grouping_idx
                        else "",
                        "Demographic": str(row[demographic_idx]).strip()
                        if len(row) > demographic_idx
                        else "",
                        "Description": str(row[description_idx]).strip()
                        if len(row) > description_idx
                        else "",
                    }

                    if any(
                        [
                            row_dict["Category"],
                            row_dict["Grouping"],
                            row_dict["Demographic"],
                            row_dict["Description"],
                        ]
                    ):
                        sheets_data.append(row_dict)

            self.sheets_data_cache = sheets_data
            self.cache_timestamp = current_time

            print(f"✅ Successfully loaded {len(sheets_data)} rows from Google Sheets")
            return sheets_data

        except Exception as e:
            print(f"❌ Google Sheets API Error: {e}")
            # Return cached data if available, even if expired
            if self.sheets_data_cache:
                print("🔄 Using cached data due to API error")
                return self.sheets_data_cache
            return []

    def search_demographics(self, query, request_more=False):
        """INTELLIGENT search function with smart conversation handling"""
        start_time = time.time()

        try:
            # SMART DETECTION: Auto-detect "more options" requests
            is_more_request = detect_more_options_request(query)

            # Create session key for conversation tracking
            session_key = create_session_key(query)

            # Use cache only for initial requests, not for "more" requests
            cache_key = session_key
            if cache_key in SEARCH_CACHE and not is_more_request:
                cached_result = SEARCH_CACHE[cache_key].copy()
                cached_result["cache_hit"] = True
                cached_result["session_key"] = session_key
                return cached_result

            sheets_data = self._get_sheets_data()
            if not sheets_data:
                return {
                    "success": False,
                    "response": "I'm unable to access the targeting database right now. Please try again or contact ernesto@artemistargeting.com for assistance.",
                    "error": "No data available",
                }

            # Extract core query terms for searching (remove "more options" noise)
            core_query = query
            if is_more_request:
                # Clean query of "more options" language for better searching
                noise_words = [
                    "more",
                    "additional",
                    "other",
                    "else",
                    "different",
                    "what",
                    "show",
                    "give",
                    "find",
                ]
                query_words = query.lower().split()
                core_words = [word for word in query_words if word not in noise_words]
                if core_words:
                    core_query = " ".join(core_words)

            matches = search_in_data(core_query, sheets_data)

            # If no matches, try individual words as fallback
            if not matches:
                words = [
                    word
                    for word in core_query.lower().split()
                    if len(word) > 3
                    and word
                    not in ["the", "and", "for", "with", "like", "want", "need", "that", "this"]
                ]
                for word in words[:3]:
                    fallback_matches = search_in_data(word, sheets_data)
                    if fallback_matches:
                        matches = fallback_matches
                        break

            # Use smart response formatter with session tracking
            formatted_response = format_response_smart(matches, query, session_key, is_more_request)

            result = {
                "success": formatted_response["success"],
                "response": formatted_response["response"],
                "pathways": formatted_response.get("pathways", []),
                "query": core_query,
                "original_query": query,
                "matches_found": len(matches),
                "total_available": formatted_response.get("total_available", 0),
                "search_method": "intelligent_conversation_aware",
                "response_time": round(time.time() - start_time, 2),
                "cache_hit": False,
                "is_more_request": is_more_request,
                "session_key": session_key,
                "session_info": formatted_response.get("session_info", {}),
            }

            # Cache successful initial results (but not "more" requests)
            if result["success"] and len(SEARCH_CACHE) < CACHE_SIZE_LIMIT and not is_more_request:
                SEARCH_CACHE[cache_key] = result.copy()

            return result

        except Exception as e:
            return {
                "success": False,
                "response": "I'm experiencing technical difficulties searching the database. Please try again or contact ernesto@artemistargeting.com for assistance.",
                "error": str(e),
                "query": query,
                "response_time": round(time.time() - start_time, 2),
            }


# Global instance
sheets_searcher = SheetsSearcher()


def search_sheets_data(query):
    """Main function called by MCP server with INTELLIGENT conversation awareness"""
    return sheets_searcher.search_demographics(query)


# Cleanup old conversation states (run periodically)
def cleanup_old_sessions():
    """Remove conversation states older than 1 hour"""
    global CONVERSATION_STATE
    current_time = time.time()
    expired_sessions = []

    for session_key, session_data in CONVERSATION_STATE.items():
        if current_time - session_data.get("last_query_time", 0) > 3600:  # 1 hour
            expired_sessions.append(session_key)

    for session_key in expired_sessions:
        del CONVERSATION_STATE[session_key]
