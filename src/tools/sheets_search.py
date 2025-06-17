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


def is_automotive_content(text):
    """BULLETPROOF automotive detection - blocks ALL automotive categories"""
    if not text:
        return False
    text_lower = text.lower().strip()

    # COMPREHENSIVE automotive category blocking
    automotive_categories = [
        "auto intenders",
        "auto lifestyle",
        "auto owners",
        "auto sales and service",
    ]

    # Block entire automotive categories
    for auto_cat in automotive_categories:
        if auto_cat in text_lower:
            return True

    # Block specific automotive terms
    automotive_terms = [
        "in market for auto",
        "make and model of owned vehicle",
        "style of owned vehicle",
        "auto fuel type",
        "auto model",
        "auto style code",
        "ford ecosport",
        "honda passport",
        "kia sportage",
        "land rover",
        "mitsubishi outlander",
        "ford bronco sport",
        "hyundai santa fe sport",
        "chevrolet captiva sport",
        "sports car",  # This is automotive, not sports
        "sport/dual motorcycles",
        "motorcycle type class",
        "recreational vehicles",
        "sport atv",
    ]

    for term in automotive_terms:
        if term in text_lower:
            return True

    return False


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


def calculate_fitness_focused_similarity(query_text, row_data):
    """LASER-FOCUSED fitness/gym targeting with MASSIVE fitness boost"""

    category = str(row_data.get("Category", "")).strip().lower()
    grouping = str(row_data.get("Grouping", "")).strip().lower()
    demographic = str(row_data.get("Demographic", "")).strip().lower()
    description = str(row_data.get("Description", "")).strip().lower()

    combined_text = f"{category} {grouping} {demographic} {description}"
    query_lower = query_text.lower().strip()

    # BULLETPROOF automotive blocking
    wants_auto = is_automotive_query(query_text)
    if not wants_auto:
        if is_automotive_content(combined_text):
            return 0.0

    score = 0.0

    # DETECT FITNESS/GYM INTENT
    fitness_keywords = [
        "gym",
        "fitness",
        "exercise",
        "workout",
        "health",
        "sports",
        "athletic",
        "active",
    ]
    has_fitness_intent = any(keyword in query_lower for keyword in fitness_keywords)

    if has_fitness_intent:
        # MASSIVE FITNESS PRIORITY SCORING

        # PRIORITY 1: EXACT FITNESS MATCHES (10000+ points)
        exact_fitness_matches = {
            "gyms & fitness clubs": 10000,  # Direct gym targeting
            "gym - frequent visitor": 9500,  # Mobile location gym visitors
            "fitness enthusiast": 9000,  # Lifestyle fitness enthusiasts
            "fitness moms": 8500,  # Household fitness demographics
            "fitness dads": 8500,  # Household fitness demographics
            "health & fitness": 8000,  # Health & fitness category
            "personal fitness & exercise": 7500,  # Sports & recreation fitness
            "activewear - high end": 7000,  # Purchase predictors activewear
            "athletic shoe stores": 6500,  # Purchase predictors athletic shoes
            "sporting goods shoppers": 6000,  # Mobile location sporting goods
            "new years gym membership buyers": 5500,  # Purchase predictors gym
            "fitness device wearer": 5000,  # Social media fitness devices
            "interest in fitness": 4500,  # Household indicators fitness
            "interest in sports": 4000,  # Household indicators sports
            "sports enthusiast": 3500,  # Lifestyle sports enthusiasts
        }

        for exact_match, points in exact_fitness_matches.items():
            if exact_match in combined_text:
                score += points
                print(f"🎯 EXACT FITNESS MATCH: {exact_match} (+{points} points)")

        # PRIORITY 2: FITNESS CATEGORY BOOSTS (5000+ points)
        fitness_categories = {
            "purchase predictors": 5000,  # Rich fitness data
            "mobile location models": 4500,  # Gym visitors, sporting goods
            "household behaviors & interests": 4000,  # Health & fitness
            "lifestyle propensities": 3500,  # Fitness enthusiasts
            "household demographics": 3000,  # Fitness moms/dads
            "household indicators": 2500,  # Interest in fitness
            "social media models": 2000,  # Fitness device wearers
        }

        for fit_cat, points in fitness_categories.items():
            if fit_cat in category:
                score += points
                print(f"🏋️ FITNESS CATEGORY: {fit_cat} (+{points} points)")

        # PRIORITY 3: FITNESS GROUPING MATCHES (3000+ points)
        fitness_groupings = {
            "retail shoppers": 3000,  # Gyms & fitness clubs, activewear
            "venue visitors": 2800,  # Gym visitors
            "store visitors": 2600,  # Sporting goods shoppers
            "health & fitness": 2400,  # Direct health & fitness
            "sports & recreation": 2200,  # Personal fitness & exercise
            "activity & interests": 2000,  # Fitness enthusiast
            "parents - moms": 1800,  # Fitness moms
            "parents - dads": 1800,  # Fitness dads
            "interests": 1600,  # Interest in fitness
            "social media - propensities": 1400,  # Fitness device wearer
        }

        for fit_group, points in fitness_groupings.items():
            if fit_group in grouping:
                score += points
                print(f"🎪 FITNESS GROUPING: {fit_group} (+{points} points)")

        # PRIORITY 4: FITNESS WORD MATCHING (1000+ points each)
        fitness_words = [
            "gym",
            "fitness",
            "exercise",
            "workout",
            "athletic",
            "sport",
            "active",
            "health",
        ]
        for word in fitness_words:
            if word in combined_text:
                score += 1000
                print(f"💪 FITNESS WORD: {word} (+1000 points)")

    else:
        # NON-FITNESS QUERIES: Standard scoring with severe fitness penalties

        # PENALTY: Heavily penalize fitness content for non-fitness queries
        fitness_indicators = ["gym", "fitness", "exercise", "workout", "athletic", "sport"]
        for indicator in fitness_indicators:
            if indicator in combined_text:
                score -= 5000  # MASSIVE penalty

        # Standard scoring for non-fitness queries
        for word in query_lower.split():
            if len(word) > 3:
                if word in combined_text:
                    score += 50

        if query_lower in combined_text:
            score += 100

    # FINAL CATEGORY BALANCING
    if "household demographics" in category and not has_fitness_intent:
        score *= 0.3  # Reduce household demographics for non-fitness
    elif "purchase predictors" in category and has_fitness_intent:
        score *= 2.0  # Boost purchase predictors for fitness

    return max(0, score)  # Never negative


def search_in_data(query, sheets_data):
    """Search with FITNESS-FIRST priority and bulletproof automotive filtering"""

    all_matches = []
    wants_auto = is_automotive_query(query)

    # Process up to 3000 rows for maximum coverage
    max_rows = min(len(sheets_data), 3000)

    for row in sheets_data[:max_rows]:
        category = str(row.get("Category", "")).strip()
        grouping = str(row.get("Grouping", "")).strip()
        demographic = str(row.get("Demographic", "")).strip()
        description = str(row.get("Description", "")).strip()

        all_text = f"{category} {grouping} {demographic} {description}"

        # BULLETPROOF automotive filtering
        if not wants_auto:
            if is_automotive_content(all_text):
                continue

        # Calculate fitness-focused similarity score
        similarity_score = calculate_fitness_focused_similarity(query, row)

        if similarity_score > 0.1:
            all_matches.append(
                {"row": row, "score": similarity_score, "similarity": similarity_score}
            )

    # Sort by score (highest first)
    all_matches.sort(key=lambda x: x["score"], reverse=True)

    print(f"🔍 Found {len(all_matches)} total matches")
    if all_matches:
        print(f"🥇 Top score: {all_matches[0]['score']}")
        top_pathway = f"{all_matches[0]['row'].get('Category', '')} → {all_matches[0]['row'].get('Grouping', '')} → {all_matches[0]['row'].get('Demographic', '')}"
        print(f"🎯 Top pathway: {top_pathway}")

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

        # Enhanced category diversity
        category_count = category_counts.get(category, 0)
        max_per_category = 10 if "purchase predictors" in category.lower() else 6
        if category_count >= max_per_category:
            continue

        final_matches.append(match)
        seen_pathways.add(pathway)
        category_counts[category] = category_count + 1

        # Stop at 15 total matches for excellent selection
        if len(final_matches) >= 15:
            break

    print(f"✅ Final matches: {len(final_matches)}")
    return final_matches


def format_no_repeat_response(matches, query, core_key, is_more_request=False):
    """GUARANTEED NO-REPEAT response formatting with fitness emphasis"""

    global GLOBAL_SHOWN_PATHWAYS

    if not matches:
        return {
            "success": False,
            "response": f"""I couldn't find strong matches in our targeting database for '{query}'.

**For fitness/gym targeting, try specific terms like:**
- gym members, fitness enthusiasts, health conscious consumers
- people who go to the gym, workout enthusiasts, athletic consumers  
- activewear shoppers, sporting goods buyers, fitness equipment purchasers

You can also schedule a consultation with ernesto@artemistargeting.com for personalized assistance.""",
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

**Want to explore more fitness audiences? Try:**
- Different fitness activities (gym equipment, supplements, athletic wear)
- Specific sports interests (running, cycling, weightlifting, yoga)
- Health categories (nutrition, wellness, organic foods)

Or schedule a consultation with ernesto@artemistargeting.com for custom targeting strategies.""",
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
                "score": match["score"],  # Include score for debugging
            }
        )

    # Format response text with fitness context
    if is_more_request:
        response_parts = ["Here are additional fitness/gym targeting pathways:\n"]
    else:
        response_parts = [
            "Based on your fitness/gym audience description, here are the targeting pathways:\n"
        ]

    for i, pathway_data in enumerate(pathways, 1):
        response_parts.append(f"**{i}.** {pathway_data['pathway']}")
        if pathway_data["description"]:
            response_parts.append(f"   _{pathway_data['description']}_")
        response_parts.append(f"   *Relevance Score: {pathway_data['score']:.0f}*\n")

    # Show remaining count
    remaining_new = len(available_matches) - len(selected_matches)
    if remaining_new > 0:
        response_parts.append(f"**{remaining_new} more fitness targeting combinations available.**")
        response_parts.append("Ask for 'more targeting options' to see additional pathways.")

    response_parts.append(
        "\nThese pathways work together to effectively reach your fitness/gym target audience."
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
        """FITNESS-FOCUSED search with bulletproof automotive blocking"""
        start_time = time.time()

        try:
            print(f"🔍 SEARCHING FOR: {query}")

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
                "search_method": "fitness_focused_laser_targeting",
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
    """Main function called by MCP server with FITNESS-FOCUSED targeting"""
    return sheets_searcher.search_demographics(query)
