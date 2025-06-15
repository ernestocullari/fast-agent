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

# NUCLEAR automotive bias prevention - ZERO tolerance for non-auto queries
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
]

AUTOMOTIVE_CATEGORIES = ["Automotive", "Auto", "Car", "Vehicle", "Transportation"]

# Enhanced semantic mappings
SEMANTIC_MAPPINGS = {
    "home improvement": [
        "home renovation",
        "home repair",
        "house renovation",
        "property improvement",
        "remodeling",
        "home upgrade",
    ],
    "home": ["house", "property", "residence", "household", "dwelling", "homeowners"],
    "hardware": [
        "home improvement",
        "tools",
        "building supplies",
        "construction materials",
        "home depot",
        "lowes",
    ],
    "hardwood": [
        "wood flooring",
        "hardwood floors",
        "wooden floors",
        "timber flooring",
        "floor installation",
        "flooring",
    ],
    "flooring": [
        "hardwood",
        "carpet",
        "tile",
        "laminate",
        "wood floors",
        "floor installation",
        "vinyl",
        "floor covering",
    ],
    "kitchen": ["kitchen renovation", "kitchen remodel", "culinary", "cooking space", "appliances"],
    "bathroom": ["bathroom renovation", "bath remodel", "restroom upgrade", "bathroom fixtures"],
    "fitness": [
        "gym",
        "exercise",
        "workout",
        "health club",
        "athletic",
        "training",
        "bodybuilding",
    ],
    "health": ["wellness", "medical", "healthcare", "fitness", "nutrition", "diet"],
    "gym": ["fitness center", "health club", "workout facility", "exercise", "training"],
    "travel": ["tourism", "vacation", "holiday", "trip", "leisure", "getaway"],
    "hotel": ["accommodation", "lodging", "hospitality", "resort", "motel", "inn"],
    "shopping": ["retail", "buying", "purchasing", "consumer behavior", "shoppers", "buyers"],
    "retail": ["shopping", "store", "commerce", "merchant", "outlet", "mall"],
    "restaurant": ["dining", "food service", "eatery", "cuisine", "food", "bar"],
    "fashion": ["clothing", "apparel", "style", "designer", "clothes", "garments"],
    "beauty": ["cosmetics", "skincare", "makeup", "personal care", "salon", "spa"],
    "luxury": ["premium", "high-end", "upscale", "exclusive", "affluent", "wealthy"],
    "technology": ["tech", "digital", "electronics", "gadgets", "computers", "software"],
    "education": ["learning", "school", "university", "academic", "students", "teaching"],
    "finance": ["banking", "financial", "money", "investment", "loans", "credit"],
    "professional": ["business", "corporate", "career", "work", "office", "executive"],
    "families": ["parents", "children", "household", "family", "kids", "parenting"],
    "young": ["millennials", "gen z", "youth", "college", "students", "early career"],
    "seniors": ["elderly", "retirees", "retirement", "older adults", "mature", "golden years"],
    "affluent": ["wealthy", "high income", "upper class", "luxury", "premium", "upscale"],
    "budget": ["affordable", "discount", "value", "economical", "savings", "deals"],
    "market": ["shopping", "buyers", "consumers", "intenders", "prospects", "audience"],
    "improvement": ["renovation", "upgrade", "remodel", "repair", "enhancement", "makeover"],
    "shoppers": ["buyers", "customers", "purchasers", "consumers", "patrons", "clients"],
    "healthcare": [
        "medical",
        "health",
        "wellness",
        "hospital",
        "clinic",
        "healthcare professionals",
    ],
    "professionals": [
        "business people",
        "executives",
        "corporate",
        "career-focused",
        "working adults",
    ],
    "enthusiasts": ["fans", "devotees", "hobbyists", "passionate consumers", "aficionados"],
    "intenders": ["in market", "shoppers", "ready to buy", "considering purchase", "prospects"],
    "customers": ["buyers", "shoppers", "consumers", "clients", "patrons", "purchasers"],
}


def is_automotive_content(text):
    """Check if content is automotive-related"""
    text_lower = text.lower()
    return any(term in text_lower for term in AUTOMOTIVE_TERMS)


def is_automotive_query(query):
    """Check if user explicitly wants automotive content - STRICT CHECK"""
    query_lower = query.lower()
    # Must contain explicit automotive terms to be considered automotive query
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
        "nissan",
        "dealership",
        "dealer",
        "motor",
        "engine",
    ]
    return any(term in query_lower for term in explicit_auto_terms)


def calculate_bias_multiplier(row_data, query):
    """NUCLEAR bias prevention - Eliminate automotive unless explicitly requested"""
    category = str(row_data.get("Category", "")).strip()
    grouping = str(row_data.get("Grouping", "")).strip()
    demographic = str(row_data.get("Demographic", "")).strip()
    description = str(row_data.get("Description", "")).strip()

    # Check if this is automotive content
    all_text = f"{category} {grouping} {demographic} {description}"
    is_auto = is_automotive_content(all_text)

    # Check if user wants automotive content
    wants_auto = is_automotive_query(query)

    if is_auto:
        if wants_auto:
            return 1.0  # Normal scoring if explicitly requested
        else:
            return 0.0001  # NUCLEAR: 99.99% elimination for non-auto queries
    else:
        return 10.0  # 1000% boost for non-automotive content


def expand_search_terms(query):
    """Expand search terms with semantic mappings - NO automotive expansion for non-auto queries"""
    query_lower = query.lower().strip()
    expanded_terms = [{"term": query_lower, "weight": 2.0}]

    # Only expand automotive terms if query is explicitly automotive
    wants_auto = is_automotive_query(query)

    # Add semantic expansions
    for key, synonyms in SEMANTIC_MAPPINGS.items():
        if key in query_lower:
            # Skip automotive expansions unless explicitly requested
            if key in AUTOMOTIVE_TERMS and not wants_auto:
                continue

            base_weight = 0.2 if key in AUTOMOTIVE_TERMS else 2.0
            expanded_terms.append({"term": key, "weight": base_weight})

            for synonym in synonyms[:4]:
                weight = base_weight - 0.1
                expanded_terms.append({"term": synonym, "weight": weight})

    # Add individual words with ZERO automotive weight unless requested
    words = query_lower.split()
    for word in words:
        if len(word) > 2:
            if word in AUTOMOTIVE_TERMS and not wants_auto:
                continue  # Skip automotive words completely
            weight = 0.1 if word in AUTOMOTIVE_TERMS else 1.8
            expanded_terms.append({"term": word, "weight": weight})

    # Remove duplicates and sort by weight
    seen_terms = {}
    for item in expanded_terms:
        term = item["term"]
        if term not in seen_terms or item["weight"] > seen_terms[term]["weight"]:
            seen_terms[term] = item

    final_terms = list(seen_terms.values())
    final_terms.sort(key=lambda x: x["weight"], reverse=True)

    return final_terms[:12]


def calculate_similarity(text1, text2):
    """Calculate similarity between two texts with enhanced matching"""
    if not text1 or not text2:
        return 0.0

    t1_lower = text1.lower()
    t2_lower = text2.lower()

    # Exact match
    if t1_lower == t2_lower:
        return 1.0

    # Contains match (both directions)
    if t1_lower in t2_lower:
        return 0.9

    if t2_lower in t1_lower:
        return 0.85

    # Word overlap scoring (enhanced)
    words1 = set(t1_lower.split())
    words2 = set(t2_lower.split())

    if words1 and words2:
        overlap = len(words1.intersection(words2))
        total = len(words1.union(words2))
        if total > 0:
            overlap_score = overlap / total

            # BOOST: Extra scoring for exact word matches
            exact_matches = 0
            for word in words1:
                if word in words2 and len(word) > 3:
                    exact_matches += 1

            # Apply word match bonus
            word_bonus = min(exact_matches * 0.25, 0.75)
            final_score = overlap_score + word_bonus

            if final_score > 0.15:
                return min(final_score, 0.95)

    # Fuzzy matching
    similarity = difflib.SequenceMatcher(None, t1_lower, t2_lower).ratio()
    return similarity


def search_in_data(query, sheets_data):
    """Search through sheets data with NUCLEAR automotive bias prevention"""
    expanded_terms = expand_search_terms(query)
    all_matches = []
    wants_auto = is_automotive_query(query)

    max_rows = min(len(sheets_data), 800)

    for row in sheets_data[:max_rows]:
        # NUCLEAR: Skip automotive rows entirely unless explicitly requested
        category = str(row.get("Category", "")).strip()
        grouping = str(row.get("Grouping", "")).strip()
        demographic = str(row.get("Demographic", "")).strip()
        description = str(row.get("Description", "")).strip()

        all_text = f"{category} {grouping} {demographic} {description}"
        if is_automotive_content(all_text) and not wants_auto:
            continue  # SKIP automotive content completely

        best_score = 0
        best_match = None

        # Calculate bias multiplier for this row
        bias_multiplier = calculate_bias_multiplier(row, query)

        # Search in all columns with priority order
        columns = ["Description", "Demographic", "Grouping", "Category"]
        column_weights = {"Description": 1.0, "Demographic": 0.8, "Grouping": 0.6, "Category": 0.4}

        for column in columns:
            column_text = str(row.get(column, "")).strip()
            if not column_text:
                continue

            column_weight = column_weights[column]

            for term_data in expanded_terms:
                term = term_data["term"]
                weight = term_data["weight"]

                similarity = calculate_similarity(term, column_text)
                if similarity > 0.08:
                    score = similarity * weight * bias_multiplier * column_weight
                    if score > best_score:
                        best_score = score
                        best_match = {
                            "row": row,
                            "score": score,
                            "column": column,
                            "similarity": similarity,
                            "term_used": term,
                            "bias_multiplier": bias_multiplier,
                        }

        if best_match and best_score > 0.3:
            all_matches.append(best_match)

    # Sort by score and remove duplicates
    all_matches.sort(key=lambda x: x["score"], reverse=True)

    # HARDCODED REQUIREMENT: Ensure diversity and minimum 2 combinations
    final_matches = []
    seen_pathways = set()
    seen_categories = {}

    for match in all_matches:
        row = match["row"]
        category = row.get("Category", "")

        # HARDCODED: STRICT TAXONOMIC ORDER - Category → Grouping → Demographic
        pathway = f"{category} → {row.get('Grouping', '')} → {row.get('Demographic', '')}"

        if pathway in seen_pathways:
            continue

        # NUCLEAR: Double-check no automotive content unless requested
        if (
            is_automotive_content(
                f"{category} {row.get('Grouping', '')} {row.get('Demographic', '')}"
            )
            and not wants_auto
        ):
            continue

        # Limit per category for diversity (max 3 per category to ensure variety)
        category_count = seen_categories.get(category, 0)
        if category_count >= 3:
            continue

        final_matches.append(match)
        seen_pathways.add(pathway)
        seen_categories[category] = category_count + 1

        # HARDCODED: Stop at 8 matches to have good selection
        if len(final_matches) >= 8:
            break

    return final_matches


def format_response_hardcoded(matches, query, request_more=False):
    """HARDCODED response formatting with strict requirements"""

    if not matches:
        query_lower = query.lower()
        suggestions = []

        # Provide category-specific suggestions (no automotive unless requested)
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
• {suggestion_text}
• Include demographics (age, income, lifestyle) 
• Mention specific interests and behaviors

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
        # If we have more than 2, add up to 4 total for initial response
        if len(matches) > 2:
            selected_matches.extend(matches[2:4])

    # HARDCODED: Ensure minimum 2 combinations
    if len(selected_matches) < 2 and len(matches) >= 2:
        selected_matches = matches[:2]

    # HARDCODED: Build response with strict taxonomic format
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

    # HARDCODED: Format response text
    response_parts = ["Based on your audience description, here are the targeting pathways:\n"]

    for i, pathway_data in enumerate(pathways, 1):
        response_parts.append(f"**{i}.** {pathway_data['pathway']}")
        if pathway_data["description"]:
            response_parts.append(f"   _{pathway_data['description']}_\n")

    # HARDCODED: Add "more options" info if available
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
        """HARDCODED search function with strict requirements"""
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
                "search_method": "hardcoded_requirements_nuclear_prevention",
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
    """Main function called by MCP server with HARDCODED requirements"""
    return sheets_searcher.search_demographics(query)
