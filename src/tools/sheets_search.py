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

# Nuclear automotive bias prevention
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
}


def is_automotive_content(text):
    """Check if content is automotive-related"""
    text_lower = text.lower()
    return any(term in text_lower for term in AUTOMOTIVE_TERMS)


def is_automotive_query(query):
    """Check if user explicitly wants automotive content"""
    query_lower = query.lower()
    return any(term in query_lower for term in AUTOMOTIVE_TERMS[:15])  # Check top automotive terms


def calculate_bias_multiplier(row_data, query):
    """Calculate bias multiplier to reduce automotive dominance"""
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
            return 1.0  # No penalty if explicitly requested
        else:
            return 0.01  # 99% penalty for automotive when not requested
    else:
        return 10.0  # 1000% boost for non-automotive content (increased for debugging)


def expand_search_terms(query):
    """Expand search terms with semantic mappings"""
    query_lower = query.lower().strip()
    expanded_terms = [{"term": query_lower, "weight": 2.0}]

    # Add semantic expansions
    for key, synonyms in SEMANTIC_MAPPINGS.items():
        if key in query_lower:
            base_weight = (
                0.2 if key in AUTOMOTIVE_TERMS else 2.0
            )  # Higher weight for non-automotive
            expanded_terms.append({"term": key, "weight": base_weight})

            for synonym in synonyms[:4]:  # Include more synonyms
                weight = base_weight - 0.1
                expanded_terms.append({"term": synonym, "weight": weight})

    # Add individual words with better weighting
    words = query_lower.split()
    for word in words:
        if len(word) > 2:
            weight = (
                0.1 if word in AUTOMOTIVE_TERMS else 1.8
            )  # Higher weight for non-automotive words
            expanded_terms.append({"term": word, "weight": weight})

    # Remove duplicates and sort by weight
    seen_terms = {}
    for item in expanded_terms:
        term = item["term"]
        if term not in seen_terms or item["weight"] > seen_terms[term]["weight"]:
            seen_terms[term] = item

    final_terms = list(seen_terms.values())
    final_terms.sort(key=lambda x: x["weight"], reverse=True)

    return final_terms[:15]  # Return top 15 terms for better coverage


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
            if overlap_score > 0.1:  # Very low threshold
                return 0.3 + (overlap_score * 0.6)  # Higher scoring

    # Fuzzy matching with higher baseline
    similarity = difflib.SequenceMatcher(None, t1_lower, t2_lower).ratio()
    return similarity


def search_in_data(query, sheets_data):
    """Search through sheets data with bias correction and debug output"""
    expanded_terms = expand_search_terms(query)
    all_matches = []

    # Debug: Print some info about the search
    print(f"DEBUG: Searching for '{query}' in {len(sheets_data)} rows")
    print(f"DEBUG: Expanded terms: {[t['term'] for t in expanded_terms[:5]]}")

    max_rows = min(len(sheets_data), 1000)  # Increased for debugging

    for i, row in enumerate(sheets_data[:max_rows]):
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
                if similarity > 0.01:  # ULTRA low threshold - should match almost anything
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
                            "column_text": column_text[:50],  # For debugging
                        }

        if best_match and best_score > 0.01:  # ULTRA low threshold - should match almost anything
            all_matches.append(best_match)
            # Debug: Print first few matches
            if len(all_matches) <= 3:
                print(
                    f"DEBUG: Match {len(all_matches)}: {best_match['term_used']} -> {best_match['column_text']} (score: {best_score:.3f})"
                )

    print(f"DEBUG: Found {len(all_matches)} total matches before filtering")

    # Sort by score and remove duplicates
    all_matches.sort(key=lambda x: x["score"], reverse=True)

    # Ensure diversity and limit automotive results
    final_matches = []
    automotive_count = 0
    max_automotive = 5 if is_automotive_query(query) else 1  # Allow more if explicitly requested
    seen_pathways = set()
    seen_categories = {}

    for match in all_matches:
        row = match["row"]
        category = row.get("Category", "")
        pathway = f"{category} → {row.get('Grouping', '')} → {row.get('Demographic', '')}"

        if pathway in seen_pathways:
            continue

        # Check if automotive
        is_auto = is_automotive_content(
            f"{category} {row.get('Grouping', '')} {row.get('Demographic', '')}"
        )

        if is_auto:
            if automotive_count >= max_automotive:
                continue
            automotive_count += 1

        # Limit per category for diversity
        category_count = seen_categories.get(category, 0)
        if category_count >= 3:  # Max 3 per category (increased for debugging)
            continue

        final_matches.append(match)
        seen_pathways.add(pathway)
        seen_categories[category] = category_count + 1

        if len(final_matches) >= 10:  # Increased for debugging
            break

    print(f"DEBUG: Returning {len(final_matches)} final matches")
    return final_matches


def format_response(matches, query):
    """Format the response for n8n with debug info"""
    if not matches:
        # Enhanced no-match response with better suggestions
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
        else:
            suggestions = [
                "high income households",
                "affluent professionals",
                "premium shoppers",
                "luxury consumers",
            ]

        suggestion_text = ", ".join(suggestions[:3])

        return f"""I couldn't find strong matches in our targeting database for '{query}'.

Try being more specific with terms like:
• {suggestion_text}
• Include demographics (age, income, lifestyle) 
• Mention specific interests and behaviors

**DEBUG INFO**: Ultra-low thresholds are active for debugging. If you're still not seeing matches, there may be a data access issue.

You can also explore our targeting tool or schedule a consultation with ernesto@artemistargeting.com for personalized assistance."""

    response_parts = ["Based on your audience description, here are the targeting pathways:\n"]

    # Add debug info for successful matches
    response_parts.append(f"**DEBUG**: Found {len(matches)} matches with ultra-low thresholds\n")

    if len(matches) == 1:
        match = matches[0]
        row = match["row"]
        pathway = (
            f"{row.get('Category', '')} → {row.get('Grouping', '')} → {row.get('Demographic', '')}"
        )
        response_parts.append("🎯 **Primary Targeting:**")
        response_parts.append(f"• {pathway}")
        response_parts.append(
            f"  *Match score: {match['score']:.3f}, Term: '{match['term_used']}'*"
        )

        description = row.get("Description", "")
        if description:
            desc_text = description[:120].strip()
            response_parts.append(f"  _{desc_text}..._")

    elif len(matches) == 2:
        response_parts.append("🎯 **Targeting Combination:**")
        for i, match in enumerate(matches):
            row = match["row"]
            pathway = f"{row.get('Category', '')} → {row.get('Grouping', '')} → {row.get('Demographic', '')}"
            response_parts.append(f"• {pathway}")
            response_parts.append(f"  *Score: {match['score']:.3f}*")

        # Add description from best match
        best_match = matches[0]
        description = best_match["row"].get("Description", "")
        if description:
            desc_text = description[:100].strip()
            response_parts.append(f"\n_{desc_text}..._")

    else:
        response_parts.append("🎯 **Targeting Options:**")
        for i, match in enumerate(matches[:5]):  # Show top 5
            row = match["row"]
            pathway = f"{row.get('Category', '')} → {row.get('Grouping', '')} → {row.get('Demographic', '')}"
            response_parts.append(f"• {pathway}")
            response_parts.append(f"  *Score: {match['score']:.3f}*")

        # Show additional options if available
        if len(matches) > 5:
            response_parts.append(
                f"\n**Additional Options:** {len(matches) - 5} more targeting pathways found"
            )

        # Add description from best match
        best_match = matches[0]
        description = best_match["row"].get("Description", "")
        if description:
            desc_text = description[:100].strip()
            response_parts.append(f"\n_{desc_text}..._")

    response_parts.append(
        "\nThese pathways work together to effectively reach your target audience."
    )

    return "\n".join(response_parts)


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
        """Get and cache sheets data with debug output"""
        current_time = time.time()

        # Use cache if fresh (5 minutes)
        if (
            self.sheets_data_cache
            and self.cache_timestamp
            and current_time - self.cache_timestamp < 300
        ):
            print(f"DEBUG: Using cached data with {len(self.sheets_data_cache)} rows")
            return self.sheets_data_cache

        # Fetch fresh data
        try:
            print(f"DEBUG: Fetching fresh data from sheet ID: {self.sheet_id}")
            sheet = self.service.spreadsheets()
            result = (
                sheet.values()
                .get(
                    spreadsheetId=self.sheet_id,
                    range="A:D",
                )
                .execute()
            )

            values = result.get("values", [])
            if not values:
                print("DEBUG: No values returned from Google Sheet")
                return []

            headers = values[0]
            data_rows = values[1:]
            print(f"DEBUG: Retrieved {len(data_rows)} data rows from sheet")
            print(f"DEBUG: Headers: {headers}")

            # Find column indices
            try:
                category_idx = headers.index("Category")
                grouping_idx = headers.index("Grouping")
                demographic_idx = headers.index("Demographic")
                description_idx = headers.index("Description")
                print(
                    f"DEBUG: Column indices found - Category: {category_idx}, Grouping: {grouping_idx}, Demographic: {demographic_idx}, Description: {description_idx}"
                )
            except ValueError as e:
                print(f"DEBUG: Column not found: {e}")
                print(f"DEBUG: Available headers: {headers}")
                return []

            # Convert to dictionaries
            sheets_data = []
            for i, row in enumerate(data_rows):
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

                    # Skip empty rows
                    if any(
                        [
                            row_dict["Category"],
                            row_dict["Grouping"],
                            row_dict["Demographic"],
                            row_dict["Description"],
                        ]
                    ):
                        sheets_data.append(row_dict)
                        # Print first few rows for debugging
                        if i < 3:
                            print(f"DEBUG: Row {i + 1}: {row_dict}")

            print(f"DEBUG: Processed {len(sheets_data)} valid rows")

            # Cache results
            self.sheets_data_cache = sheets_data
            self.cache_timestamp = current_time

            return sheets_data

        except Exception as e:
            print(f"DEBUG: Error fetching sheets data: {e}")
            return []

    def search_demographics(self, query):
        """Main search function with enhanced fallback logic and debug output"""
        start_time = time.time()

        try:
            print(f"DEBUG: Starting search for query: '{query}'")

            # Check cache
            cache_key = query.lower().strip()
            if cache_key in SEARCH_CACHE:
                cached_result = SEARCH_CACHE[cache_key].copy()
                cached_result["cache_hit"] = True
                print("DEBUG: Returning cached result")
                return cached_result

            # Get sheets data
            sheets_data = self._get_sheets_data()
            if not sheets_data:
                print("DEBUG: No sheets data available")
                return {
                    "success": False,
                    "response": "I'm unable to access the targeting database right now. Please try again or contact ernesto@artemistargeting.com for assistance.",
                    "error": "No data available",
                }

            # Primary search with bias correction
            matches = search_in_data(query, sheets_data)

            # If no matches, try with individual key words
            if not matches:
                print("DEBUG: No matches found, trying fallback search with individual words")
                # Extract key words and try again
                words = [
                    word
                    for word in query.lower().split()
                    if len(word) > 3
                    and word not in ["the", "and", "for", "with", "like", "want", "need"]
                ]
                for word in words[:3]:  # Try top 3 words
                    print(f"DEBUG: Trying fallback search with word: '{word}'")
                    fallback_matches = search_in_data(word, sheets_data)
                    if fallback_matches:
                        matches = fallback_matches[:3]  # Limit fallback results
                        print(f"DEBUG: Fallback search found {len(matches)} matches")
                        break

            # Format response
            response_text = format_response(matches, query)
            success = len(matches) > 0

            result = {
                "success": success,
                "response": response_text,
                "query": query,
                "matches_found": len(matches),
                "search_method": "ultra_debug_nuclear_bias_corrected",
                "response_time": round(time.time() - start_time, 2),
                "cache_hit": False,
                "debug_info": {"sheet_rows": len(sheets_data), "ultra_low_thresholds": True},
            }

            # Cache successful results
            if success and len(SEARCH_CACHE) < CACHE_SIZE_LIMIT:
                SEARCH_CACHE[cache_key] = result.copy()

            print(f"DEBUG: Search completed. Success: {success}, Matches: {len(matches)}")
            return result

        except Exception as e:
            print(f"DEBUG: Exception in search_demographics: {e}")
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
    """Main function called by MCP server"""
    return sheets_searcher.search_demographics(query)
