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
    "acura", "audi", "bmw", "buick", "cadillac", "chevrolet", "chevy", "chrysler", 
    "dodge", "ford", "gmc", "honda", "hyundai", "infiniti", "jaguar", "jeep", "kia", 
    "lexus", "lincoln", "mazda", "mercedes", "benz", "mitsubishi", "nissan", "pontiac", 
    "porsche", "ram", "subaru", "toyota", "volkswagen", "volvo", "car", "auto", 
    "vehicle", "truck", "suv", "sedan", "coupe", "convertible", "dealership", 
    "automotive", "motor", "engine", "transmission", "brake", "cars", "autos", 
    "vehicles", "trucks", "suvs", "sedans", "coupes", "convertibles", "dealers", 
    "dealerships", "motors", "engines", "transmissions", "brakes"
]

def is_automotive_content(text):
    """Check if content is automotive-related"""
    text_lower = text.lower()
    return any(term in text_lower for term in AUTOMOTIVE_TERMS)

def is_automotive_query(query):
    """Check if user explicitly wants automotive content"""
    query_lower = query.lower()
    explicit_auto_terms = [
        "car", "auto", "vehicle", "truck", "suv", "sedan", "automotive", 
        "bmw", "mercedes", "toyota", "honda", "ford", "chevrolet", 
        "nissan", "dealership", "dealer", "motor", "engine"
    ]
    return any(term in query_lower for term in explicit_auto_terms)

def calculate_enhanced_similarity(query_text, row_data):
    """Enhanced similarity calculation prioritizing exact matches"""
    
    # Combine all searchable fields
    category = str(row_data.get('Category', '')).strip()
    grouping = str(row_data.get('Grouping', '')).strip() 
    demographic = str(row_data.get('Demographic', '')).strip()
    description = str(row_data.get('Description', '')).strip()
    
    combined_text = f"{category} {grouping} {demographic} {description}".lower()
    query_lower = query_text.lower().strip()
    
    # NUCLEAR: Absolutely no automotive results unless explicitly requested
    if is_automotive_content(combined_text) and not is_automotive_query(query_text):
        return 0.0
    
    # Initialize score
    score = 0.0
    
    # 1. EXACT PHRASE MATCHING (highest priority)
    if query_lower in combined_text:
        score += 0.9
        
    # 2. EXACT WORD MATCHING (very high priority) 
    query_words = set(query_lower.split())
    text_words = set(combined_text.split())
    
    # Count exact word matches
    exact_matches = len(query_words.intersection(text_words))
    if exact_matches > 0:
        word_match_ratio = exact_matches / len(query_words)
        score += word_match_ratio * 0.7
    
    # 3. PARTIAL WORD MATCHING for longer words
    for query_word in query_words:
        if len(query_word) >= 4:  # Only for substantial words
            for text_word in text_words:
                if len(text_word) >= 4:
                    if query_word in text_word or text_word in query_word:
                        score += 0.3
                        break
    
    # 4. BOOST FOR DESCRIPTION FIELD (most detailed)
    if query_lower in description.lower():
        score += 0.4
        
    # 5. BOOST FOR DEMOGRAPHIC FIELD (most specific)
    if query_lower in demographic.lower():
        score += 0.3
    
    # 6. Common semantic matches (hardcoded for reliability)
    semantic_boosts = {
        'hardwood': ['floor', 'flooring'],
        'floor': ['hardwood', 'flooring'], 
        'floors': ['hardwood', 'flooring'],
        'flooring': ['hardwood', 'floor'],
        'shop': ['shopper', 'shopping', 'store'],
        'shopping': ['shopper', 'shop', 'store'],
        'buy': ['buyer', 'shopper', 'purchase'],
        'home': ['house', 'household', 'residence'],
        'improvement': ['renovation', 'remodel', 'upgrade'],
        'travel': ['vacation', 'trip', 'tourist'],
        'health': ['fitness', 'wellness', 'medical'],
        'luxury': ['premium', 'upscale', 'affluent']
    }
    
    for query_word in query_words:
        if query_word in semantic_boosts:
            related_words = semantic_boosts[query_word]
            for related_word in related_words:
                if related_word in combined_text:
                    score += 0.2
                    break
    
    return min(score, 1.0)  # Cap at 1.0

def search_in_data(query, sheets_data):
    """Search through sheets data with enhanced matching"""
    
    all_matches = []
    wants_auto = is_automotive_query(query)
    
    # Process up to 1000 rows for better coverage
    max_rows = min(len(sheets_data), 1000)
    
    for row in sheets_data[:max_rows]:
        # Skip automotive content unless explicitly requested
        category = str(row.get("Category", "")).strip()
        grouping = str(row.get("Grouping", "")).strip()
        demographic = str(row.get("Demographic", "")).strip()
        description = str(row.get("Description", "")).strip()
        
        all_text = f"{category} {grouping} {demographic} {description}"
        if is_automotive_content(all_text) and not wants_auto:
            continue
            
        # Calculate similarity score
        similarity_score = calculate_enhanced_similarity(query, row)
        
        if similarity_score > 0.1:  # Much lower threshold to catch more matches
            all_matches.append({
                "row": row,
                "score": similarity_score,
                "similarity": similarity_score
            })
    
    # Sort by score
    all_matches.sort(key=lambda x: x["score"], reverse=True)
    
    # Remove duplicates while maintaining diversity
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
            
        # Double-check no automotive unless requested
        if is_automotive_content(pathway) and not wants_auto:
            continue
            
        # Limit per category for diversity (max 2 per category)
        category_count = seen_categories.get(category, 0)
        if category_count >= 2:
            continue
            
        final_matches.append(match)
        seen_pathways.add(pathway)
        seen_categories[category] = category_count + 1
        
        # Stop at 8 total matches
        if len(final_matches) >= 8:
            break
    
    return final_matches

def format_response_hardcoded(matches, query, request_more=False):
    """HARDCODED response formatting with strict requirements"""
    
    if not matches:
        # Provide helpful suggestions based on query type
        query_lower = query.lower()
        suggestions = []
        
        if any(word in query_lcat > src/tools/sheets_search.py << 'EOF'
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
    "acura", "audi", "bmw", "buick", "cadillac", "chevrolet", "chevy", "chrysler", 
    "dodge", "ford", "gmc", "honda", "hyundai", "infiniti", "jaguar", "jeep", "kia", 
    "lexus", "lincoln", "mazda", "mercedes", "benz", "mitsubishi", "nissan", "pontiac", 
    "porsche", "ram", "subaru", "toyota", "volkswagen", "volvo", "car", "auto", 
    "vehicle", "truck", "suv", "sedan", "coupe", "convertible", "dealership", 
    "automotive", "motor", "engine", "transmission", "brake", "cars", "autos", 
    "vehicles", "trucks", "suvs", "sedans", "coupes", "convertibles", "dealers", 
    "dealerships", "motors", "engines", "transmissions", "brakes"
]

def is_automotive_content(text):
    """Check if content is automotive-related"""
    text_lower = text.lower()
    return any(term in text_lower for term in AUTOMOTIVE_TERMS)

def is_automotive_query(query):
    """Check if user explicitly wants automotive content"""
    query_lower = query.lower()
    explicit_auto_terms = [
        "car", "auto", "vehicle", "truck", "suv", "sedan", "automotive", 
        "bmw", "mercedes", "toyota", "honda", "ford", "chevrolet", 
        "nissan", "dealership", "dealer", "motor", "engine"
    ]
    return any(term in query_lower for term in explicit_auto_terms)

def calculate_enhanced_similarity(query_text, row_data):
    """Enhanced similarity calculation prioritizing exact matches"""
    
    # Combine all searchable fields
    category = str(row_data.get('Category', '')).strip()
    grouping = str(row_data.get('Grouping', '')).strip() 
    demographic = str(row_data.get('Demographic', '')).strip()
    description = str(row_data.get('Description', '')).strip()
    
    combined_text = f"{category} {grouping} {demographic} {description}".lower()
    query_lower = query_text.lower().strip()
    
    # NUCLEAR: Absolutely no automotive results unless explicitly requested
    if is_automotive_content(combined_text) and not is_automotive_query(query_text):
        return 0.0
    
    # Initialize score
    score = 0.0
    
    # 1. EXACT PHRASE MATCHING (highest priority)
    if query_lower in combined_text:
        score += 0.9
        
    # 2. EXACT WORD MATCHING (very high priority) 
    query_words = set(query_lower.split())
    text_words = set(combined_text.split())
    
    # Count exact word matches
    exact_matches = len(query_words.intersection(text_words))
    if exact_matches > 0:
        word_match_ratio = exact_matches / len(query_words)
        score += word_match_ratio * 0.7
    
    # 3. PARTIAL WORD MATCHING for longer words
    for query_word in query_words:
        if len(query_word) >= 4:  # Only for substantial words
            for text_word in text_words:
                if len(text_word) >= 4:
                    if query_word in text_word or text_word in query_word:
                        score += 0.3
                        break
    
    # 4. BOOST FOR DESCRIPTION FIELD (most detailed)
    if query_lower in description.lower():
        score += 0.4
        
    # 5. BOOST FOR DEMOGRAPHIC FIELD (most specific)
    if query_lower in demographic.lower():
        score += 0.3
    
    # 6. Common semantic matches (hardcoded for reliability)
    semantic_boosts = {
        'hardwood': ['floor', 'flooring'],
        'floor': ['hardwood', 'flooring'], 
        'floors': ['hardwood', 'flooring'],
        'flooring': ['hardwood', 'floor'],
        'shop': ['shopper', 'shopping', 'store'],
        'shopping': ['shopper', 'shop', 'store'],
        'buy': ['buyer', 'shopper', 'purchase'],
        'home': ['house', 'household', 'residence'],
        'improvement': ['renovation', 'remodel', 'upgrade'],
        'travel': ['vacation', 'trip', 'tourist'],
        'health': ['fitness', 'wellness', 'medical'],
        'luxury': ['premium', 'upscale', 'affluent']
    }
    
    for query_word in query_words:
        if query_word in semantic_boosts:
            related_words = semantic_boosts[query_word]
            for related_word in related_words:
                if related_word in combined_text:
                    score += 0.2
                    break
    
    return min(score, 1.0)  # Cap at 1.0

def search_in_data(query, sheets_data):
    """Search through sheets data with enhanced matching"""
    
    all_matches = []
    wants_auto = is_automotive_query(query)
    
    # Process up to 1000 rows for better coverage
    max_rows = min(len(sheets_data), 1000)
    
    for row in sheets_data[:max_rows]:
        # Skip automotive content unless explicitly requested
        category = str(row.get("Category", "")).strip()
        grouping = str(row.get("Grouping", "")).strip()
        demographic = str(row.get("Demographic", "")).strip()
        description = str(row.get("Description", "")).strip()
        
        all_text = f"{category} {grouping} {demographic} {description}"
        if is_automotive_content(all_text) and not wants_auto:
            continue
            
        # Calculate similarity score
        similarity_score = calculate_enhanced_similarity(query, row)
        
        if similarity_score > 0.1:  # Much lower threshold to catch more matches
            all_matches.append({
                "row": row,
                "score": similarity_score,
                "similarity": similarity_score
            })
    
    # Sort by score
    all_matches.sort(key=lambda x: x["score"], reverse=True)
    
    # Remove duplicates while maintaining diversity
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
            
        # Double-check no automotive unless requested
        if is_automotive_content(pathway) and not wants_auto:
            continue
            
        # Limit per category for diversity (max 2 per category)
        category_count = seen_categories.get(category, 0)
        if category_count >= 2:
            continue
            
        final_matches.append(match)
        seen_pathways.add(pathway)
        seen_categories[category] = category_count + 1
        
        # Stop at 8 total matches
        if len(final_matches) >= 8:
            break
    
    return final_matches

def format_response_hardcoded(matches, query, request_more=False):
    """HARDCODED response formatting with strict requirements"""
    
    if not matches:
        # Provide helpful suggestions based on query type
        query_lower = query.lower()
        suggestions = []
        
        if any(word in query_lower for word in ["home", "house", "improvement", "renovation", "hardware", "flooring", "hardwood", "kitchen", "bathroom"]):
            suggestions = ["home improvement shoppers", "hardware store visitors", "home renovation intenders", "flooring shoppers"]
        elif any(word in query_lower for word in ["health", "fitness", "gym", "wellness", "nutrition", "exercise"]):
            suggestions = ["health conscious consumers", "fitness enthusiasts", "wellness shoppers", "gym members"]
        elif any(word in query_lower for word in ["fashion", "shopping", "retail", "clothing", "style", "beauty"]):
            suggestions = ["fashion shoppers", "retail enthusiasts", "luxury shoppers", "brand conscious consumers"]
        elif any(word in query_lower for word in ["travel", "hotel", "vacation", "tourism", "leisure"]):
            suggestions = ["hotel guests", "business travelers", "vacation planners", "luxury travel shoppers"]
        elif any(word in query_lower for word in ["food", "restaurant", "dining", "coffee"]):
            suggestions = ["restaurant visitors", "fine dining enthusiasts", "coffee shop customers", "food enthusiasts"]
        else:
            suggestions = ["high income households", "affluent professionals", "premium shoppers", "luxury consumers"]
        
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
        pathways.append({
            "pathway": pathway,
            "description": description[:150] + "..." if len(description) > 150 else description,
        })
    
    # Format response text
    response_parts = ["Based on your audience description, here are the targeting pathways:\n"]
    
    for i, pathway_data in enumerate(pathways, 1):
        response_parts.append(f"**{i}.** {pathway_data['pathway']}")
        if pathway_data["description"]:
            response_parts.append(f"   _{pathway_data['description']}_\n")
    
    # Add "more options" info if available
    remaining_matches = len(matches) - len(selected_matches)
    if remaining_matches > 0:
        response_parts.append(f"**Additional Options Available:** {remaining_matches} more targeting combinations")
        response_parts.append("Ask for 'more targeting options' to see additional pathways.")
    
    response_parts.append("\nThese pathways work together to effectively reach your target audience.")
    
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
                        "Category": str(row[category_idx]).strip() if len(row) > category_idx else "",
                        "Grouping": str(row[grouping_idx]).strip() if len(row) > grouping_idx else "",
                        "Demographic": str(row[demographic_idx]).strip() if len(row) > demographic_idx else "",
                        "Description": str(row[description_idx]).strip() if len(row) > description_idx else "",
                    }

                    if any([
                        row_dict["Category"],
                        row_dict["Grouping"], 
                        row_dict["Demographic"],
                        row_dict["Description"],
                    ]):
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

            # If no matches, try individual words as fallback
            if not matches:
                words = [
                    word for word in original_query.lower().split()
                    if len(word) > 3 and word not in ["the", "and", "for", "with", "like", "want", "need", "that", "this"]
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
                "search_method": "enhanced_similarity_matching",
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

# Enhanced deployment trigger
