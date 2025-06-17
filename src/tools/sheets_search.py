import os
import json
import time
import difflib
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Performance optimizations
SEARCH_CACHE = {}
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


def calculate_enhanced_similarity(query_text, row_data):
    """ENHANCED version with STRONGER fitness targeting"""

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

    # ENHANCED SEMANTIC MAPPINGS - Much stronger fitness targeting
    enhanced_mappings = {
        # FITNESS - SUPERCHARGED targeting
        "fitness": [
            "purchase predictors",  # Gyms & Fitness Clubs - HIGHEST PRIORITY
            "household behaviors & interests",  # Health & Fitness, Sports & Recreation
            "lifestyle propensities",  # Fitness Enthusiast
            "household indicators",  # Interest in fitness
            "household demographics",  # Fitness Moms/Dads
        ],
        "gym": [
            "purchase predictors",  # Gyms & Fitness Clubs - PRIORITY 1
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
        # Health & Wellness - ENHANCED
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

    # PRIORITY 1: SUPER BOOSTED category matching for fitness
    query_words = query_lower.split()
    for word in query_words:
        if word in enhanced_mappings:
            target_categories = enhanced_mappings[word]
            for target_cat in target_categories:
                if target_cat in category:
                    # MEGA BOOST for fitness-related terms
                    if word in ["fitness", "gym", "gyms", "exercise", "workout", "enthusiasts"]:
                        score += 300.0  # MASSIVE fitness boost
                    else:
                        score += 150.0  # Standard category match
                    break

    # PRIORITY 2: Grouping and demographic matching with fitness boost
    for word in query_words:
        if len(word) > 3:
            # SUPER BOOST for fitness in grouping/demographic
            fitness_terms = ["fitness", "gym", "exercise", "workout", "health"]
            if any(fitness_term in grouping for fitness_term in fitness_terms):
                score += 200.0  # Huge fitness grouping boost
            elif any(fitness_term in demographic for fitness_term in fitness_terms):
                score += 180.0  # Big fitness demographic boost
            elif word in grouping:
                score += 100.0
            elif word in demographic:
                score += 80.0

    # PRIORITY 3: Description matching with fitness emphasis
    for word in query_words:
        if len(word) > 3:
            if word in description:
                # Extra boost for fitness-related descriptions
                if any(
                    fit_word in description
                    for fit_word in ["gym", "fitness", "exercise", "workout"]
                ):
                    score += 100.0  # Big fitness description boost
                else:
                    score += 50.0

    # PRIORITY 4: Direct text matching
    if query_lower in combined_text:
        score += 30.0

    # PRIORITY 5: Individual word matching with fitness boost
    for word in query_words:
        if len(word) > 3:
            if word in combined_text:
                if word in ["fitness", "gym", "gyms", "exercise", "workout"]:
                    score += 25.0  # Fitness word boost
                else:
                    score += 10.0

    # ENHANCED CATEGORY DIVERSITY BOOSTING
    if "household demographics" in category:
        score *= 0.3  # MAJOR reduction for household demographics
    elif "purchase predictors" in category:
        score *= 2.0  # MAJOR boost for purchase predictors (has gym data)
    elif "household behaviors & interests" in category:
        score *= 1.8  # Big boost for behaviors & interests
    elif "lifestyle propensities" in category:
        score *= 1.7  # Good boost for lifestyle propensities
    elif "consumer models" in category:
        score *= 1.6  # Moderate boost for consumer models

    return score


def search_in_data(query, sheets_data):
    """Search through sheets data with BULLETPROOF automotive filtering"""

    all_matches = []
    wants_auto = is_automotive_query(query)

    # Process up to 1000 rows for better coverage
    max_rows = min(len(sheets_data), 1000)

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

        # IMPROVED: Allow more fitness-related entries per category
        category_count = category_counts.get(category, 0)
        # Allow up to 4 entries for Purchase Predictors (has gym data), 2 for others
        max_per_category = 4 if "purchase predictors" in category.lower() else 2
        if category_count >= max_per_category:
            continue

        final_matches.append(match)
        seen_pathways.add(pathway)
        category_counts[category] = category_count + 1

        # Stop at 20 total matches for better selection
        if len(final_matches) >= 20:
            break

    return final_matches


def format_response_hardcoded(matches, query, request_more=False):
    """ENHANCED response formatting with proper more options handling"""

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

    # ENHANCED: Proper "more options" handling to prevent duplicates
    if request_more and len(matches) > 3:
        # For "more options" requests, return next 3 combinations (4-6)
        selected_matches = matches[3:6] if len(matches) > 5 else matches[3:]
        # If not enough new ones, take from end of list
        if len(selected_matches) < 3 and len(matches) > 6:
            selected_matches.extend(matches[6:9])
    else:
        # Initial request: return first 3 combinations
        selected_matches = matches[:3]

    # Ensure we have at least 3 results if available
    if len(selected_matches) < 3 and len(matches) >= 3:
        selected_matches = matches[:3]

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
    response_parts = ["Based on your audience description, here are the targeting pathways:\n"]

    for i, pathway_data in enumerate(pathways, 1):
        response_parts.append(f"**{i}.** {pathway_data['pathway']}")
        if pathway_data["description"]:
            response_parts.append(f"   _{pathway_data['description']}_\n")

    # Add "more options" info if available
    remaining_matches = len(matches) - len(selected_matches)
    if remaining_matches > 0:
        response_parts.append(
            f"**Additional Options Available:** {remaining_matches} more targeting combinations"
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
        "request_more": request_more,
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
        """ENHANCED search function with proper more options handling"""
        start_time = time.time()

        try:
            # ENHANCED: Better detection of "more options" requests
            more_indicators = ["more", "additional", "other", "different", "else"]
            if any(indicator in query.lower() for indicator in more_indicators) and any(
                word in query.lower() for word in ["option", "combination", "targeting", "pathway"]
            ):
                request_more = True
                # Keep original query for context
                original_query = query
            else:
                original_query = query

            # Create cache key based on core query terms (not "more" indicators)
            core_query = original_query.lower()
            for indicator in more_indicators + ["option", "combination", "targeting", "pathway"]:
                core_query = core_query.replace(indicator, "").strip()

            cache_key = core_query.lower().strip()

            # For "more" requests, don't use cache - always get fresh results
            if cache_key in SEARCH_CACHE and not request_more:
                cached_result = SEARCH_CACHE[cache_key].copy()
                cached_result["cache_hit"] = True
                return cached_result

            sheets_data = self._get_sheets_data()
            if not sheets_data:
                return {
                    "success": False,
                    "response": "I'm unable to access the targeting database right now. Please try again or contact ernesto@artemistargeting.com for assistance.",
                    "error": "No data available",
                }

            # Use core query for searching, not the "more options" request
            search_query = core_query if request_more else original_query
            matches = search_in_data(search_query, sheets_data)

            # If no matches, try individual words as fallback
            if not matches:
                words = [
                    word
                    for word in search_query.lower().split()
                    if len(word) > 3
                    and word
                    not in ["the", "and", "for", "with", "like", "want", "need", "that", "this"]
                ]
                for word in words[:3]:
                    fallback_matches = search_in_data(word, sheets_data)
                    if fallback_matches:
                        matches = fallback_matches
                        break

            # Use enhanced response formatter
            formatted_response = format_response_hardcoded(matches, search_query, request_more)

            result = {
                "success": formatted_response["success"],
                "response": formatted_response["response"],
                "pathways": formatted_response.get("pathways", []),
                "query": search_query,
                "matches_found": len(matches),
                "total_available": formatted_response.get("total_available", 0),
                "search_method": "enhanced_fitness_targeting",
                "response_time": round(time.time() - start_time, 2),
                "cache_hit": False,
                "request_more": request_more,
            }

            # Cache successful results (but not "more" requests)
            if result["success"] and len(SEARCH_CACHE) < CACHE_SIZE_LIMIT and not request_more:
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
    """Main function called by MCP server with ENHANCED fitness targeting"""
    return sheets_searcher.search_demographics(query)
