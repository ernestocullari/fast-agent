import os
import json
import time
import difflib
import hashlib
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Performance optimizations
SEARCH_CACHE = {}
GLOBAL_SHOWN_PATHWAYS = {}  # Track shown pathways per core query
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
    "tesla",
    "ferrari",
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
    """Detect 'more options' requests using natural language patterns"""
    query_lower = query.lower().strip()

    more_patterns = [
        "more",
        "additional",
        "other",
        "else",
        "different",
        "another",
        "alternative",
        "what else",
        "show me more",
        "give me more",
        "more options",
        "additional options",
        "other combinations",
        "something else",
        "alternatives",
        "any other",
    ]

    return any(pattern in query_lower for pattern in more_patterns)


def create_core_query_key(query):
    """Create a key based on core query terms (ignoring 'more' indicators)"""
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
        "pathways",
        "please",
        "can",
        "you",
    ]

    words = query.lower().split()
    core_words = [word for word in words if word not in stop_words and len(word) > 2]
    core_query = " ".join(sorted(core_words))
    return hashlib.md5(core_query.encode()).hexdigest()[:16]


def calculate_database_aligned_similarity(query_text, row_data):
    """PERFECTLY ALIGNED with actual Google Sheets data structure"""

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

    # DATABASE-ALIGNED SEMANTIC MAPPINGS based on actual CSV structure
    database_mappings = {
        # FITNESS - Aligned with actual Purchase Predictors data
        "fitness": [
            "gyms & fitness clubs",  # Exact match in Purchase Predictors
            "health & fitness",  # In Household Behaviors & Interests
            "personal fitness & exercise",  # In Sports & Recreation
            "fitness enthusiast",  # In Lifestyle Propensities
            "fitness mom/dad",  # In Household Demographics
        ],
        "gym": [
            "gyms & fitness clubs",  # Direct Purchase Predictors match
            "health & fitness",
            "personal fitness & exercise",
        ],
        "exercise": [
            "personal fitness & exercise",  # Direct Sports & Recreation match
            "gyms & fitness clubs",
            "health & fitness",
        ],
        "workout": ["gyms & fitness clubs", "personal fitness & exercise", "health & fitness"],
        # HEALTH - Aligned with Health & Natural Foods grouping
        "health": [
            "health & natural foods",  # Direct Household Behaviors match
            "health & fitness",
            "health and well being",
            "organic and natural",  # In Consumer Models
        ],
        "wellness": ["health and well being", "health & fitness", "health & natural foods"],
        "organic": [
            "organic and natural",  # Direct Consumer Models match
            "organic grocery",  # In Purchase Predictors
            "health & natural foods",
        ],
        "natural": ["organic and natural", "health & natural foods", "natural health remedies"],
        # FINANCIAL - Aligned with Consumer Financial Insights
        "financial": [
            "consumer financial insights",  # Direct category match
            "financial services",
        ],
        "investment": [
            "consumer financial insights",
            "investment shoppers",  # In Purchase Predictors
        ],
        "wealth": ["consumer financial insights", "premium lifestyle"],
        # HOME - Aligned with Home Property data
        "home": [
            "home property",  # Direct category match
            "home improvement",  # In Purchase Predictors
            "home furnishings",
        ],
        "improvement": [
            "home improvement",  # Direct Purchase Predictors match
            "home property",
            "diy",
        ],
        # SHOPPING - Aligned with Purchase Predictors
        "shopping": [
            "retail shoppers",  # In Purchase Predictors
            "purchase predictors",  # Category match
            "online behavior models",
        ],
        "retail": ["retail shoppers", "luxury retail stores", "purchase predictors"],
    }

    # PRIORITY 1: Perfect category/grouping matching (500+ points)
    query_words = query_lower.split()
    for word in query_words:
        if word in database_mappings:
            target_terms = database_mappings[word]
            for target_term in target_terms:
                if target_term in grouping:
                    score += 500.0  # MAXIMUM boost for grouping match
                    break
                elif target_term in category:
                    score += 400.0  # High boost for category match
                    break

    # PRIORITY 2: Direct demographic matching (300+ points)
    for word in query_words:
        if len(word) > 3:
            if word in demographic:
                score += 300.0

    # PRIORITY 3: Description keyword matching (200+ points)
    for word in query_words:
        if len(word) > 3:
            if word in description:
                score += 200.0

    # PRIORITY 4: Partial text matching (100+ points)
    if query_lower in combined_text:
        score += 100.0

    # PRIORITY 5: Individual word matching (50+ points each)
    for word in query_words:
        if len(word) > 3 and word in combined_text:
            score += 50.0

    # CATEGORY BALANCING - Reduce household demographics dominance
    if "household demographics" in category:
        score *= 0.3  # 70% reduction for household demographics
    elif "purchase predictors" in category:
        score *= 1.5  # 50% boost for purchase predictors
    elif "household behaviors & interests" in category:
        score *= 1.4  # 40% boost for behaviors & interests
    elif "lifestyle propensities" in category:
        score *= 1.3  # 30% boost for lifestyle propensities

    return score


def search_in_data(query, sheets_data):
    """Search with ZERO repetition guarantee"""

    all_matches = []
    wants_auto = is_automotive_query(query)

    # Process up to 2000 rows for maximum coverage
    max_rows = min(len(sheets_data), 2000)

    for row in sheets_data[:max_rows]:
        category = str(row.get("Category", "")).strip()
        grouping = str(row.get("Grouping", "")).strip()
        demographic = str(row.get("Demographic", "")).strip()
        description = str(row.get("Description", "")).strip()

        all_text = f"{category} {grouping} {demographic} {description}"

        # BULLETPROOF automotive filtering
        if not wants_auto:
            if (
                is_automotive_content(category)
                or is_automotive_content(grouping)
                or is_automotive_content(demographic)
                or is_automotive_content(description)
                or is_automotive_content(all_text)
            ):
                continue

        # Calculate database-aligned similarity score
        similarity_score = calculate_database_aligned_similarity(query, row)

        if similarity_score > 0.1:
            all_matches.append(
                {"row": row, "score": similarity_score, "similarity": similarity_score}
            )

    # Sort by score (highest first)
    all_matches.sort(key=lambda x: x["score"], reverse=True)

    # ABSOLUTE DUPLICATE PREVENTION
    final_matches = []
    seen_pathways = set()
    category_counts = {}

    for match in all_matches:
        row = match["row"]
        category = row.get("Category", "")

        # Create EXACT pathway identifier
        pathway = f"{category} → {row.get('Grouping', '')} → {row.get('Demographic', '')}"

        # ZERO TOLERANCE for duplicates
        if pathway in seen_pathways:
            continue

        # Final automotive check
        if not wants_auto and is_automotive_content(pathway.lower()):
            continue

        # Category diversity (max 4 per category for variety)
        category_count = category_counts.get(category, 0)
        if category_count >= 4:
            continue

        final_matches.append(match)
        seen_pathways.add(pathway)
        category_counts[category] = category_count + 1

        # Stop at 20 total matches for optimal selection
        if len(final_matches) >= 20:
            break

    return final_matches


def format_no_repeat_response(matches, query, core_key, is_more_request=False):
    """GUARANTEED NO-REPEAT response formatting"""

    global GLOBAL_SHOWN_PATHWAYS

    if not matches:
        return {
            "success": False,
            "response": f"""I couldn't find strong matches in our targeting database for '{query}'.

Try being more specific with terms like:
- Include specific interests (fitness, health, organic products)
- Mention demographics (age, income, lifestyle)
- Describe behaviors (shopping habits, brand preferences)

You can also explore our targeting tool or schedule a consultation with ernesto@artemistargeting.com for personalized assistance.""",
            "pathways": [],
            "query": query,
        }

    # Initialize tracking for this core query if needed
    if core_key not in GLOBAL_SHOWN_PATHWAYS:
        GLOBAL_SHOWN_PATHWAYS[core_key] = set()

    shown_set = GLOBAL_SHOWN_PATHWAYS[core_key]

    # Filter out ALL previously shown pathways for this core query
    available_matches = []
    for match in matches:
        row = match["row"]
        pathway = (
            f"{row.get('Category', '')} → {row.get('Grouping', '')} → {row.get('Demographic', '')}"
        )

        if pathway not in shown_set:
            available_matches.append(match)

    # If we've exhausted new options, provide helpful message
    if len(available_matches) == 0:
        return {
            "success": True,
            "response": f"""I've shown you all the best targeting combinations for '{query}' from our database.

**Options to explore:**
- Try a different audience description
- Use more specific terms (fitness enthusiasts, organic shoppers, etc.)
- Schedule a consultation with ernesto@artemistargeting.com for custom targeting strategies

Would you like to explore targeting for a different audience?""",
            "pathways": [],
            "query": query,
            "exhausted": True,
        }

    # Select up to 3 NEW pathways
    selected_matches = available_matches[:3]

    # Track the pathways we're showing NOW
    pathways = []
    for match in selected_matches:
        row = match["row"]
        category = str(row.get("Category", "")).strip()
        grouping = str(row.get("Grouping", "")).strip()
        demographic = str(row.get("Demographic", "")).strip()
        description = str(row.get("Description", "")).strip()

        pathway = f"{category} → {grouping} → {demographic}"

        # ADD to shown set immediately
        shown_set.add(pathway)

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

    # Show remaining count
    remaining_new = len(available_matches) - len(selected_matches)
    if remaining_new > 0:
        response_parts.append(f"**{remaining_new} more targeting combinations available.**")
        response_parts.append("Ask for 'more targeting options' to see additional pathways.")

    response_parts.append(
        "\nThese pathways work together to effectively reach your target audience."
    )

    return {
        "success": True,
        "response": "\n".join(response_parts),
        "pathways": [p["pathway"] for p in pathways],
        "total_available": len(matches),
        "remaining_new": remaining_new,
        "query": query,
        "is_more_request": is_more_request,
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
        """Get and cache sheets data"""
        current_time = time.time()

        if (
            self.sheets_data_cache
            and self.cache_timestamp
            and current_time - self.cache_timestamp < 1800
        ):  # 30 minutes
            return self.sheets_data_cache

        try:
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
            if self.sheets_data_cache:
                print("🔄 Using cached data due to API error")
                return self.sheets_data_cache
            return []

    def search_demographics(self, query, request_more=False):
        """ZERO-REPEAT search function with database alignment"""
        start_time = time.time()

        try:
            # Detect "more options" requests
            is_more_request = detect_more_options_request(query)

            # Create core query key for tracking
            core_key = create_core_query_key(query)

            sheets_data = self._get_sheets_data()
            if not sheets_data:
                return {
                    "success": False,
                    "response": "I'm unable to access the targeting database right now. Please try again or contact ernesto@artemistargeting.com for assistance.",
                    "error": "No data available",
                }

            # Extract core query for searching (remove "more" noise)
            core_query = query
            if is_more_request:
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
                    "me",
                    "options",
                ]
                query_words = query.lower().split()
                core_words = [word for word in query_words if word not in noise_words]
                if core_words:
                    core_query = " ".join(core_words)

            matches = search_in_data(core_query, sheets_data)

            # Fallback search if no matches
            if not matches:
                words = [
                    word
                    for word in core_query.lower().split()
                    if len(word) > 3 and word not in ["the", "and", "for", "with", "like"]
                ]
                for word in words[:3]:
                    fallback_matches = search_in_data(word, sheets_data)
                    if fallback_matches:
                        matches = fallback_matches
                        break

            # Use no-repeat formatter
            formatted_response = format_no_repeat_response(
                matches, query, core_key, is_more_request
            )

            result = {
                "success": formatted_response["success"],
                "response": formatted_response["response"],
                "pathways": formatted_response.get("pathways", []),
                "query": core_query,
                "original_query": query,
                "matches_found": len(matches),
                "total_available": formatted_response.get("total_available", 0),
                "search_method": "zero_repeat_database_aligned",
                "response_time": round(time.time() - start_time, 2),
                "is_more_request": is_more_request,
                "core_key": core_key,
            }

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
    """Main function called by MCP server with ZERO repetition guarantee"""
    return sheets_searcher.search_demographics(query)


# Cleanup function to prevent memory bloat
def cleanup_shown_pathways():
    """Clean up old pathway tracking data"""
    global GLOBAL_SHOWN_PATHWAYS
    # Keep only the 50 most recent core queries to prevent memory issues
    if len(GLOBAL_SHOWN_PATHWAYS) > 50:
        # Keep most recent entries based on usage
        keys_to_keep = list(GLOBAL_SHOWN_PATHWAYS.keys())[-50:]
        GLOBAL_SHOWN_PATHWAYS = {k: GLOBAL_SHOWN_PATHWAYS[k] for k in keys_to_keep}
