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
    ],
    "home": ["house", "property", "residence", "household", "dwelling"],
    "hardware": ["home improvement", "tools", "building supplies", "construction materials"],
    "fitness": ["gym", "exercise", "workout", "health club", "athletic"],
    "health": ["wellness", "medical", "healthcare", "fitness"],
    "travel": ["tourism", "vacation", "holiday", "trip"],
    "hotel": ["accommodation", "lodging", "hospitality", "resort"],
    "shopping": ["retail", "buying", "purchasing", "consumer behavior"],
    "restaurant": ["dining", "food service", "eatery", "cuisine"],
    "fashion": ["clothing", "apparel", "style", "designer"],
    "beauty": ["cosmetics", "skincare", "makeup", "personal care"],
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
        return 5.0  # 500% boost for non-automotive content


def expand_search_terms(query):
    """Expand search terms with semantic mappings"""
    query_lower = query.lower().strip()
    expanded_terms = [{"term": query_lower, "weight": 2.0}]

    # Add semantic expansions
    for key, synonyms in SEMANTIC_MAPPINGS.items():
        if key in query_lower:
            base_weight = 0.3 if key in AUTOMOTIVE_TERMS else 1.5
            expanded_terms.append({"term": key, "weight": base_weight})

            for synonym in synonyms[:3]:
                weight = base_weight - 0.2
                expanded_terms.append({"term": synonym, "weight": weight})

    # Add individual words
    words = query_lower.split()
    for word in words:
        if len(word) > 2:
            weight = 0.2 if word in AUTOMOTIVE_TERMS else 1.2
            expanded_terms.append({"term": word, "weight": weight})

    return expanded_terms[:8]


def calculate_similarity(text1, text2):
    """Calculate similarity between two texts"""
    if not text1 or not text2:
        return 0.0

    t1_lower = text1.lower()
    t2_lower = text2.lower()

    if t1_lower == t2_lower:
        return 1.0

    if t1_lower in t2_lower:
        return 0.8

    if t2_lower in t1_lower:
        return 0.7

    # Word overlap
    words1 = set(t1_lower.split())
    words2 = set(t2_lower.split())

    if words1 and words2:
        overlap = len(words1.intersection(words2))
        total = len(words1.union(words2))
        if total > 0:
            overlap_score = overlap / total
            if overlap_score > 0.2:
                return 0.3 + (overlap_score * 0.4)

    return difflib.SequenceMatcher(None, t1_lower, t2_lower).ratio()


def search_in_data(query, sheets_data):
    """Search through sheets data with bias correction"""
    expanded_terms = expand_search_terms(query)
    all_matches = []

    max_rows = min(len(sheets_data), 500)

    for row in sheets_data[:max_rows]:
        best_score = 0
        best_match = None

        # Calculate bias multiplier for this row
        bias_multiplier = calculate_bias_multiplier(row, query)

        # Search in all columns
        for column in ["Description", "Demographic", "Grouping", "Category"]:
            column_text = str(row.get(column, "")).strip()
            if not column_text:
                continue

            for term_data in expanded_terms:
                term = term_data["term"]
                weight = term_data["weight"]

                similarity = calculate_similarity(term, column_text)
                if similarity > 0.15:  # Lowered threshold
                    score = similarity * weight * bias_multiplier
                    if score > best_score:
                        best_score = score
                        best_match = {
                            "row": row,
                            "score": score,
                            "column": column,
                            "similarity": similarity,
                        }

        if best_match and best_score > 1:  # Very low threshold
            all_matches.append(best_match)

    # Sort by score and remove duplicates
    all_matches.sort(key=lambda x: x["score"], reverse=True)

    # Ensure diversity and limit automotive results
    final_matches = []
    automotive_count = 0
    max_automotive = 2 if is_automotive_query(query) else 0
    seen_pathways = set()

    for match in all_matches:
        row = match["row"]
        pathway = (
            f"{row.get('Category', '')} → {row.get('Grouping', '')} → {row.get('Demographic', '')}"
        )

        if pathway in seen_pathways:
            continue

        # Check if automotive
        is_auto = is_automotive_content(
            f"{row.get('Category', '')} {row.get('Grouping', '')} {row.get('Demographic', '')}"
        )

        if is_auto:
            if automotive_count >= max_automotive:
                continue
            automotive_count += 1

        final_matches.append(match)
        seen_pathways.add(pathway)

        if len(final_matches) >= 6:
            break

    return final_matches


def format_response(matches, query):
    """Format the response for n8n"""
    if not matches:
        return f"""I couldn't find strong matches in our targeting database for '{query}'.

Try being more specific with terms like:
• home improvement shoppers, hardware store visitors
• health conscious consumers, fitness enthusiasts  
• fashion shoppers, luxury shoppers
• Include demographics (age, income, lifestyle)

You can also explore our targeting tool or schedule a consultation with ernesto@artemistargeting.com for personalized assistance."""

    response_parts = ["Based on your audience description, here are the targeting pathways:\n"]

    if len(matches) == 1:
        match = matches[0]
        row = match["row"]
        pathway = (
            f"{row.get('Category', '')} → {row.get('Grouping', '')} → {row.get('Demographic', '')}"
        )
        response_parts.append("🎯 **Primary Targeting:**")
        response_parts.append(f"• {pathway}")

        description = row.get("Description", "")
        if description:
            desc_text = description[:120].strip()
            response_parts.append(f"  _{desc_text}..._")

    else:
        response_parts.append("🎯 **Targeting Combination:**")
        for match in matches[:3]:
            row = match["row"]
            pathway = f"{row.get('Category', '')} → {row.get('Grouping', '')} → {row.get('Demographic', '')}"
            response_parts.append(f"• {pathway}")

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
        """Get and cache sheets data"""
        current_time = time.time()

        # Use cache if fresh (5 minutes)
        if (
            self.sheets_data_cache
            and self.cache_timestamp
            and current_time - self.cache_timestamp < 300
        ):
            return self.sheets_data_cache

        # Fetch fresh data
        try:
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
                return []

            headers = values[0]
            data_rows = values[1:]

            # Find column indices
            category_idx = headers.index("Category")
            grouping_idx = headers.index("Grouping")
            demographic_idx = headers.index("Demographic")
            description_idx = headers.index("Description")

            # Convert to dictionaries
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

            # Cache results
            self.sheets_data_cache = sheets_data
            self.cache_timestamp = current_time

            return sheets_data

        except Exception as e:
            print(f"Error fetching sheets data: {e}")
            return []

    def search_demographics(self, query):
        """Main search function"""
        start_time = time.time()

        try:
            # Check cache
            cache_key = query.lower().strip()
            if cache_key in SEARCH_CACHE:
                cached_result = SEARCH_CACHE[cache_key].copy()
                cached_result["cache_hit"] = True
                return cached_result

            # Get sheets data
            sheets_data = self._get_sheets_data()
            if not sheets_data:
                return {
                    "success": False,
                    "response": "I'm unable to access the targeting database right now. Please try again or contact ernesto@artemistargeting.com for assistance.",
                    "error": "No data available",
                }

            # Search with bias correction
            matches = search_in_data(query, sheets_data)

            # Format response
            response_text = format_response(matches, query)
            success = len(matches) > 0

            result = {
                "success": success,
                "response": response_text,
                "query": query,
                "matches_found": len(matches),
                "search_method": "nuclear_bias_corrected",
                "response_time": round(time.time() - start_time, 2),
                "cache_hit": False,
            }

            # Cache successful results
            if success and len(SEARCH_CACHE) < CACHE_SIZE_LIMIT:
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
    """Main function called by MCP server"""
    return sheets_searcher.search_demographics(query)
