import os
import json
import time
import difflib
from typing import List, Dict, Any
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Performance optimizations
SEARCH_CACHE = {}
CACHE_SIZE_LIMIT = 100
TIMEOUT_SECONDS = 45  # Stay under Vercel's 60s limit

# Optimized semantic mappings - REDUCED for performance
SEMANTIC_MAPPINGS = {
    # Automotive & Transportation - CORE TERMS ONLY
    "car": ["auto", "vehicle"],
    "luxury car": ["premium vehicle"],
    "truck": ["pickup", "suv"],
    "buyers": ["shoppers", "intenders"],
    "automotive": ["auto", "car"],
    "bmw": ["luxury german car"],
    "lexus": ["luxury japanese car"],
    "mercedes": ["luxury car"],
    # Store Categories - CRITICAL SECTION
    "hardwood": ["wood floor", "flooring"],
    "floor": ["flooring", "hardwood"],
    "flooring": ["floor", "hardwood"],
    "coffee": ["cafe"],
    "gym": ["fitness"],
    "restaurant": ["dining"],
    "visitors": ["shoppers", "customers"],
    "hotel": ["accommodation"],
    "spa": ["wellness"],
    # Demographics & Income - SIMPLIFIED
    "high income": ["affluent", "wealthy"],
    "young": ["millennial"],
    "seniors": ["elderly"],
    # Shopping & Retail - CORE ONLY
    "shopping": ["retail", "buying"],
    "shoppers": ["buyers", "customers"],
    # Intent & Behavior - ESSENTIAL
    "in market": ["intenders", "shoppers"],
    "premium": ["luxury", "high-end"],
}

# Optimized search configuration with higher thresholds
SEARCH_HIERARCHY = {
    "Description": {"weight": 100, "priority": 1, "threshold": 0.5, "exact_match_bonus": 50},
    "Demographic": {"weight": 75, "priority": 2, "threshold": 0.5, "exact_match_bonus": 25},
    "Grouping": {"weight": 50, "priority": 3, "threshold": 0.5, "exact_match_bonus": 15},
    "Category": {"weight": 25, "priority": 4, "threshold": 0.4, "exact_match_bonus": 10},
}


class MatchResult:
    def __init__(self, row, column_triggered, match_type, similarity_score, total_score):
        self.row = row
        self.column_triggered = column_triggered
        self.match_type = match_type
        self.similarity_score = similarity_score
        self.total_score = total_score
        self.pathway = self._build_pathway()

    def _build_pathway(self):
        category = self.row.get("Category", "")
        grouping = self.row.get("Grouping", "")
        demographic = self.row.get("Demographic", "")
        return f"{category} → {grouping} → {demographic}"


def expand_search_terms(query):
    """OPTIMIZED: Limited semantic expansion for performance"""
    expanded_terms = [query]  # Start with original
    query_lower = query.lower()

    # LIMIT: Only add top 2 semantic matches
    matches_added = 0
    for term, synonyms in SEMANTIC_MAPPINGS.items():
        if term in query_lower and matches_added < 2:
            expanded_terms.extend(synonyms[:2])  # Only first 2 synonyms
            matches_added += 1

    # Add individual words for broader matching
    words = query_lower.split()
    expanded_terms.extend(words[:3])  # Max 3 words

    # PERFORMANCE: Limit total expansion to 6 terms
    seen = set()
    unique_terms = []
    for term in expanded_terms[:6]:
        if term not in seen and len(term) > 1:  # Skip single characters
            seen.add(term)
            unique_terms.append(term)

    return unique_terms


def calculate_similarity(text1, text2):
    """OPTIMIZED: Faster similarity calculation with early exit"""
    if not text1 or not text2:
        return 0.0

    t1_lower = text1.lower()
    t2_lower = text2.lower()

    # Quick exact match check
    if t1_lower == t2_lower:
        return 1.0

    # Quick contains check
    if t1_lower in t2_lower or t2_lower in t1_lower:
        return 0.8

    # Use difflib only for remaining cases
    return difflib.SequenceMatcher(None, t1_lower, t2_lower).ratio()


def search_column(expanded_queries, column_text, column_name, config, row):
    """OPTIMIZED: Early exit column search with performance limits"""
    if not column_text:
        return []

    column_lower = column_text.lower()
    matches = []

    for search_term in expanded_queries[:4]:  # LIMIT: Max 4 search terms per column
        search_lower = search_term.lower()

        if len(search_lower) < 2:  # Skip very short terms
            continue

        # PRIORITY 1: Exact full match
        if search_lower == column_lower:
            matches.append(
                {
                    "column": column_name,
                    "match_type": "exact_full",
                    "similarity_score": 1.0,
                    "total_score": config["weight"] + config["exact_match_bonus"] + 100,
                    "search_term": search_term,
                    "row": row,
                }
            )
            break  # EARLY EXIT: Found exact match

        # PRIORITY 2: Exact contains match
        elif search_lower in column_lower:
            matches.append(
                {
                    "column": column_name,
                    "match_type": "exact_contains",
                    "similarity_score": 0.9,
                    "total_score": config["weight"] + config["exact_match_bonus"] + 25,
                    "search_term": search_term,
                    "row": row,
                }
            )

        # PRIORITY 3: Reverse contains
        elif column_lower in search_lower:
            matches.append(
                {
                    "column": column_name,
                    "match_type": "reverse_contains",
                    "similarity_score": 0.85,
                    "total_score": config["weight"] + config["exact_match_bonus"],
                    "search_term": search_term,
                    "row": row,
                }
            )

        # PRIORITY 4: Fuzzy match with higher threshold
        else:
            similarity = calculate_similarity(search_lower, column_lower)
            if similarity >= config["threshold"]:
                matches.append(
                    {
                        "column": column_name,
                        "match_type": "fuzzy",
                        "similarity_score": similarity,
                        "total_score": int(config["weight"] * similarity),
                        "search_term": search_term,
                        "row": row,
                    }
                )

    return matches


def hierarchical_search(query, sheets_data):
    """OPTIMIZED: Performance-focused hierarchical search with early exits"""
    start_time = time.time()
    expanded_queries = expand_search_terms(query)
    all_matches = []
    processed_rows = 0

    # PERFORMANCE: Process maximum 500 rows to prevent timeout
    max_rows = min(len(sheets_data), 500)

    for row in sheets_data[:max_rows]:
        processed_rows += 1

        # TIMEOUT CHECK: Every 50 rows
        if processed_rows % 50 == 0:
            if time.time() - start_time > TIMEOUT_SECONDS:
                break

        # EARLY EXIT: Stop after finding 8 good matches
        if len(all_matches) >= 8:
            break

        row_matches = []

        # Level 1: Search Description first (highest priority)
        description_matches = search_column(
            expanded_queries,
            str(row.get("Description", "")),
            "Description",
            SEARCH_HIERARCHY["Description"],
            row,
        )

        # EARLY EXIT: If exact match found in Description, use it and skip other columns
        exact_description = [
            m for m in description_matches if m["match_type"] in ["exact_full", "exact_contains"]
        ]
        if exact_description:
            best_match = max(exact_description, key=lambda x: x["total_score"])
            match_result = MatchResult(
                row=row,
                column_triggered=best_match["column"],
                match_type=best_match["match_type"],
                similarity_score=best_match["similarity_score"],
                total_score=best_match["total_score"],
            )
            all_matches.append(match_result)
            continue  # Skip other columns for this row

        row_matches.extend(description_matches)

        # Level 2: Search Demographic
        demographic_matches = search_column(
            expanded_queries,
            str(row.get("Demographic", "")),
            "Demographic",
            SEARCH_HIERARCHY["Demographic"],
            row,
        )
        row_matches.extend(demographic_matches)

        # Level 3: Search Grouping
        grouping_matches = search_column(
            expanded_queries,
            str(row.get("Grouping", "")),
            "Grouping",
            SEARCH_HIERARCHY["Grouping"],
            row,
        )
        row_matches.extend(grouping_matches)

        # Level 4: Search Category (only if no good matches yet)
        if not any(m["total_score"] > 80 for m in row_matches):
            category_matches = search_column(
                expanded_queries,
                str(row.get("Category", "")),
                "Category",
                SEARCH_HIERARCHY["Category"],
                row,
            )
            row_matches.extend(category_matches)

        # Create MatchResult for best match in this row
        if row_matches:
            best_match = max(row_matches, key=lambda x: x["total_score"])
            # Only add matches above minimum threshold
            if best_match["total_score"] > 30:
                match_result = MatchResult(
                    row=row,
                    column_triggered=best_match["column"],
                    match_type=best_match["match_type"],
                    similarity_score=best_match["similarity_score"],
                    total_score=best_match["total_score"],
                )
                all_matches.append(match_result)

    # Sort by total score and return top 3 matches
    all_matches.sort(key=lambda x: x.total_score, reverse=True)
    return all_matches[:3]


def format_targeting_response(matches, original_query):
    """Format matches into clean targeting pathways"""
    if not matches:
        return generate_no_match_response(original_query)

    response_lines = []

    for i, match in enumerate(matches, 1):
        pathway = match.pathway
        description = match.row.get("Description", "")
        if description:
            response_lines.append(f"{i}. **{pathway}** - {description}")
        else:
            response_lines.append(f"{i}. **{pathway}**")

    return "\n".join(response_lines)


def generate_no_match_response(query):
    """Generate helpful no-match responses with suggestions"""
    query_lower = query.lower()
    suggestions = []

    # Category-specific suggestions
    if any(word in query_lower for word in ["car", "auto", "vehicle", "bmw", "lexus"]):
        suggestions = ["automotive shoppers", "luxury car buyers", "in market for auto"]
    elif any(word in query_lower for word in ["home", "house", "property", "floor", "hardwood"]):
        suggestions = ["home buyers", "real estate intenders", "property investors"]
    elif any(word in query_lower for word in ["health", "medical", "fitness"]):
        suggestions = ["health conscious", "fitness enthusiasts", "wellness shoppers"]
    elif any(word in query_lower for word in ["fashion", "shopping", "retail"]):
        suggestions = ["fashion shoppers", "retail enthusiasts", "online shoppers"]
    elif any(word in query_lower for word in ["hotel", "travel", "vacation", "spa"]):
        suggestions = ["hotel guests", "business travelers", "vacation planners"]
    else:
        suggestions = ["high income households", "affluent professionals", "premium shoppers"]

    suggestion_text = ", ".join(suggestions)

    return f"""No targeting pathways found in our database for '{query}'.

Try describing your audience with broader terms like:
- {suggestion_text}
- Or describe demographics (age, income, interests)
- Or mention behaviors and life stages

You can also explore our tool further or schedule a consultation with ernesto@artemistargeting.com"""


class SheetsSearcher:
    def __init__(self):
        self.service = None
        self.sheet_id = None
        self.sheets_data_cache = None
        self.cache_timestamp = None
        self._setup_sheets_api()

    def _setup_sheets_api(self):
        """Initialize Google Sheets API with service account credentials"""
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
        """OPTIMIZED: Cache Google Sheets data to reduce API calls"""
        current_time = time.time()

        # Use cached data if available and fresh (5 minutes)
        if (
            self.sheets_data_cache
            and self.cache_timestamp
            and current_time - self.cache_timestamp < 300
        ):
            return self.sheets_data_cache

        # Fetch fresh data
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
        try:
            category_idx = headers.index("Category")
            grouping_idx = headers.index("Grouping")
            demographic_idx = headers.index("Demographic")
            description_idx = headers.index("Description")
        except ValueError as e:
            raise ValueError(f"Required column not found: {e}")

        # Convert to dictionary format
        sheets_data = []
        for row in data_rows:
            if len(row) <= max(category_idx, grouping_idx, demographic_idx, description_idx):
                continue

            row_dict = {
                "Category": str(row[category_idx]).strip() if len(row) > category_idx else "",
                "Grouping": str(row[grouping_idx]).strip() if len(row) > grouping_idx else "",
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

        # Cache the results
        self.sheets_data_cache = sheets_data
        self.cache_timestamp = current_time

        return sheets_data

    def search_demographics(self, query):
        """OPTIMIZED: Enhanced search with caching and performance monitoring"""
        start_time = time.time()

        try:
            # Check cache first
            cache_key = query.lower().strip()
            if cache_key in SEARCH_CACHE:
                cached_result = SEARCH_CACHE[cache_key].copy()
                cached_result["cache_hit"] = True
                return cached_result

            # Get sheets data (cached)
            sheets_data = self._get_sheets_data()
            if not sheets_data:
                return {"success": False, "error": "No data found in sheet"}

            # Perform hierarchical search with timeout protection
            matches = hierarchical_search(query, sheets_data)

            # Process matches
            if matches:
                pathways = []
                seen_pathways = set()

                for match in matches:
                    if all(
                        [match.row["Category"], match.row["Grouping"], match.row["Demographic"]]
                    ):
                        pathway = match.pathway
                        if pathway not in seen_pathways:
                            pathways.append(pathway)
                            seen_pathways.add(pathway)

                if pathways:
                    result = {
                        "success": True,
                        "pathways": pathways,
                        "search_source": "Google Sheets Database - Optimized Search",
                        "query": query,
                        "matches_found": len(pathways),
                        "database_search": True,
                        "search_method": "semantic_hierarchical_optimized",
                        "response_time": round(time.time() - start_time, 2),
                        "cache_hit": False,
                    }

                    # Cache successful results
                    if len(SEARCH_CACHE) < CACHE_SIZE_LIMIT:
                        SEARCH_CACHE[cache_key] = result.copy()

                    return result

            # No matches found
            result = {
                "success": False,
                "message": generate_no_match_response(query),
                "query": query,
                "search_attempted": True,
                "database_searched": True,
                "search_method": "semantic_hierarchical_optimized",
                "response_time": round(time.time() - start_time, 2),
                "cache_hit": False,
            }

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Database search error: {str(e)}",
                "query": query,
                "response_time": round(time.time() - start_time, 2),
            }
