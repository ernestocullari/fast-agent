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

    # Check for automotive terms with word boundaries to avoid false positives
    for term in AUTOMOTIVE_TERMS:
        # Use word boundaries to avoid matching parts of other words
        if (
            f" {term} " in f" {text_lower} "
            or text_lower.startswith(f"{term} ")
            or text_lower.endswith(f" {term}")
            or term == text_lower  # Exact match
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
    """ENHANCED version with comprehensive semantic matching"""

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

    # ENHANCED SEMANTIC MAPPINGS
    enhanced_mappings = {
        # Health & Wellness expanded
        "health": [
            "health and well being",
            "health & fitness",
            "organic and natural",
            "personal fitness & exercise",
            "health & natural foods",
        ],
        "wellness": [
            "health and well being",
            "health & fitness",
            "organic and natural",
            "personal fitness & exercise",
            "health & natural foods",
        ],
        "fitness": [
            "health & fitness",
            "personal fitness & exercise",
            "sports & recreation",
            "health and well being",
        ],
        "gym": ["health & fitness", "personal fitness & exercise", "sports & recreation"],
        "exercise": ["health & fitness", "personal fitness & exercise", "sports & recreation"],
        "organic": [
            "organic and natural",
            "health & natural foods",
            "organic grocery",
            "health and well being",
        ],
        "natural": ["organic and natural", "health & natural foods", "organic grocery"],
        # Mental wellness & mindfulness
        "mental": [
            "health and well being",
            "health & fitness",
            "sports & recreation",
            "social causes",
        ],
        "mindfulness": [
            "health and well being",
            "sports & recreation",
            "social causes",
            "health & fitness",
        ],
        "yoga": [
            "health & fitness",
            "personal fitness & exercise",
            "sports & recreation",
            "health and well being",
        ],
        "meditation": ["health and well being", "health & fitness", "social causes"],
        # Luxury & Premium
        "luxury": ["premium lifestyle", "luxury retail stores", "luxury department store"],
        "affluent": ["premium lifestyle", "luxury retail stores", "luxury department store"],
        "premium": ["premium lifestyle", "luxury retail stores", "luxury department store"],
        "upscale": ["premium lifestyle", "luxury retail stores", "luxury department store"],
        # Financial
        "financial": ["consumer financial insights", "financial services"],
        "investment": ["consumer financial insights", "financial services"],
        "wealth": ["consumer financial insights", "financial services", "premium lifestyle"],
        # Travel
        "travel": ["travel", "vacation", "leisure"],
        "vacation": ["travel", "vacation", "leisure"],
        "hotel": ["travel", "vacation", "leisure"],
        # Home & DIY
        "home": ["home improvement", "diy", "home furnishings"],
        "improvement": ["home improvement", "diy"],
        "renovation": ["home improvement", "diy"],
        "diy": ["diy", "home improvement"],
        # Shopping & Retail
        "shopping": ["retail shoppers", "purchase predictors", "online behavior"],
        "retail": ["retail shoppers", "purchase predictors", "online behavior"],
    }

    # PRIORITY 1: Enhanced category matching (100+ points)
    query_words = query_lower.split()
    for word in query_words:
        if word in enhanced_mappings:
            target_categories = enhanced_mappings[word]
            for target_cat in target_categories:
                if target_cat in category or target_cat in grouping:
                    score += 100.0  # High score for category match
                    break

    # PRIORITY 2: Direct text matching (50+ points)
    if query_lower in combined_text:
        score += 50.0

    # PRIORITY 3: Individual word matching (10+ points each)
    for word in query_words:
        if len(word) > 3:
            if word in combined_text:
                score += 10.0

    # PRIORITY 4: Category diversity boost
    # Reduce Household Demographics dominance
    if "household demographics" in category:
        score *= 0.7  # 30% reduction for household demographics
    elif "consumer models" in category or "purchase predictors" in category:
        score *= 1.3  # 30% boost for other relevant categories

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

    # FINAL FILTER: Remove duplicates and ensure no automotive leakage
    final_matches = []
    seen_pathways = set()
    seen_categories = {}

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

        # Limit per category for diversity (max 3 per category for better results)
        category_count = seen_categories.get(category, 0)
        if category_count >= 3:
            continue

        final_matches.append(match)
        seen_pathways.add(pathway)
        seen_categories[category] = category_count + 1

        # Stop at 10 total matches for better selection
        if len(final_matches) >= 10:
            break

    return final_matches


def format_response_hardcoded(matches, query, request_more=False):
    """HARDCODED response formatting with strict requirements"""

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

    # HARDCODED REQUIREMENT: Always provide minimum 2 combinations
    if request_more and len(matches) > 2:
        # If user requests more, provide next 2 combinations
        selected_matches = matches[2:4] if len(matches) > 3 else matches[2:3]
        if len(selected_matches) < 2 and len(matches) > 4:
            selected_matches.extend(matches[4:6])
    else:
        # Always provide first 2 combinations minimum
        selected_matches = matches[:2]
        # If we have more than 2, add up to 3 total for initial response
        if len(matches) > 2:
            selected_matches.extend(matches[2:3])

    # HARDCODED: Ensure minimum 2 combinations always
    if len(selected_matches) < 2 and len(matches) >= 2:
        selected_matches = matches[:2]

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
        """Get and cache sheets data"""
        current_time = time.time()

        if (
            self.sheets_data_cache
            and self.cache_timestamp
            and current_time - self.cache_timestamp < 300
        ):
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

            return sheets_data

        except Exception as e:
            return []

    def search_demographics(self, query, request_more=False):
        """HARDCODED search function with ENHANCED semantic matching"""
        start_time = time.time()

        try:
            # Check for "more" request indicator
            if "more" in query.lower() and "option" in query.lower():
                request_more = True
                # Extract original query (remove "more options" type phrases)
                original_query = (
                    query.lower()
                    .replace("more", "")
                    .replace("option", "")
                    .replace("additional", "")
                    .strip()
                )
            else:
                original_query = query

            cache_key = original_query.lower().strip()
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

            matches = search_in_data(original_query, sheets_data)

            # If no matches, try individual words as fallback (still with automotive filtering)
            if not matches:
                words = [
                    word
                    for word in original_query.lower().split()
                    if len(word) > 3
                    and word
                    not in ["the", "and", "for", "with", "like", "want", "need", "that", "this"]
                ]
                for word in words[:3]:
                    fallback_matches = search_in_data(word, sheets_data)
                    if fallback_matches:
                        matches = fallback_matches
                        break

            # HARDCODED: Use hardcoded response formatter
            formatted_response = format_response_hardcoded(matches, original_query, request_more)

            result = {
                "success": formatted_response["success"],
                "response": formatted_response["response"],
                "pathways": formatted_response.get("pathways", []),
                "query": original_query,
                "matches_found": len(matches),
                "total_available": formatted_response.get("total_available", 0),
                "search_method": "enhanced_semantic_matching",
                "response_time": round(time.time() - start_time, 2),
                "cache_hit": False,
            }

            # Cache successful results
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
    """Main function called by MCP server with ENHANCED semantic matching"""
    return sheets_searcher.search_demographics(query)
