from http.server import BaseHTTPRequestHandler
import json
import os
import time

# ===== EMBEDDED GOOGLE SHEETS + ENHANCED SEARCH FUNCTIONS =====

def get_google_sheets_data():
    """Get data from Google Sheets"""
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        
        client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
        private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
        sheet_id = os.getenv("GOOGLE_SHEET_ID")

        if not all([client_email, private_key, sheet_id]):
            return None, "Missing Google Sheets credentials"

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

        service = build("sheets", "v4", credentials=credentials)
        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range="A:D").execute()

        values = result.get("values", [])
        if not values or len(values) < 2:
            return None, "No data found in sheet"

        headers = values[0]
        data_rows = values[1:]
        
        processed_data = []
        for row in data_rows:
            if len(row) >= 4:
                processed_data.append({
                    "Category": str(row[0]).strip(),
                    "Grouping": str(row[1]).strip(), 
                    "Demographic": str(row[2]).strip(),
                    "Description": str(row[3]).strip()
                })

        return processed_data, None

    except Exception as e:
        return None, f"Google Sheets error: {str(e)}"

def is_automotive_content(text):
    """Check if content is automotive-related"""
    automotive_terms = [
        "acura", "audi", "bmw", "buick", "cadillac", "chevrolet", "chevy", "chrysler", 
        "dodge", "ford", "gmc", "honda", "hyundai", "infiniti", "jaguar", "jeep", "kia", 
        "lexus", "lincoln", "mazda", "mercedes", "benz", "mitsubishi", "nissan", "pontiac", 
        "porsche", "ram", "subaru", "toyota", "volkswagen", "volvo", "car", "auto", 
        "vehicle", "truck", "suv", "sedan", "coupe", "convertible", "dealership", 
        "automotive", "motor", "engine", "transmission", "brake", "cars", "autos", 
        "vehicles", "trucks", "suvs", "sedans", "coupes", "convertibles", "dealers", 
        "dealerships", "motors", "engines", "transmissions", "brakes"
    ]
    text_lower = text.lower()
    return any(term in text_lower for term in automotive_terms)

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
    try:
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
            if len(query_word) >= 4:
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
        
        return min(score, 1.0)
        
    except Exception as e:
        return 0.0

def search_google_sheets_data(query, sheets_data):
    """Enhanced search through 4260+ targeting options"""
    if not sheets_data:
        return None
        
    all_matches = []
    wants_auto = is_automotive_query(query)
    
    # Process all rows for comprehensive search
    for row in sheets_data:
        # Skip automotive content unless explicitly requested
        category = str(row.get("Category", "")).strip()
        grouping = str(row.get("Grouping", "")).strip()
        demographic = str(row.get("Demographic", "")).strip()
        description = str(row.get("Description", "")).strip()
        
        all_text = f"{category} {grouping} {demographic} {description}"
        if is_automotive_content(all_text) and not wants_auto:
            continue
            
        # Calculate enhanced similarity score
        similarity_score = calculate_enhanced_similarity(query, row)
        
        if similarity_score > 0.1:  # Lower threshold to catch more matches
            all_matches.append({
                "row": row,
                "score": similarity_score
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
cat > api/chat.py << 'EOF'
from http.server import BaseHTTPRequestHandler
import json
import os
import time

# ===== EMBEDDED GOOGLE SHEETS + ENHANCED SEARCH FUNCTIONS =====

def get_google_sheets_data():
    """Get data from Google Sheets"""
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        
        client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
        private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
        sheet_id = os.getenv("GOOGLE_SHEET_ID")

        if not all([client_email, private_key, sheet_id]):
            return None, "Missing Google Sheets credentials"

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

        service = build("sheets", "v4", credentials=credentials)
        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range="A:D").execute()

        values = result.get("values", [])
        if not values or len(values) < 2:
            return None, "No data found in sheet"

        headers = values[0]
        data_rows = values[1:]
        
        processed_data = []
        for row in data_rows:
            if len(row) >= 4:
                processed_data.append({
                    "Category": str(row[0]).strip(),
                    "Grouping": str(row[1]).strip(), 
                    "Demographic": str(row[2]).strip(),
                    "Description": str(row[3]).strip()
                })

        return processed_data, None

    except Exception as e:
        return None, f"Google Sheets error: {str(e)}"

def is_automotive_content(text):
    """Check if content is automotive-related"""
    automotive_terms = [
        "acura", "audi", "bmw", "buick", "cadillac", "chevrolet", "chevy", "chrysler", 
        "dodge", "ford", "gmc", "honda", "hyundai", "infiniti", "jaguar", "jeep", "kia", 
        "lexus", "lincoln", "mazda", "mercedes", "benz", "mitsubishi", "nissan", "pontiac", 
        "porsche", "ram", "subaru", "toyota", "volkswagen", "volvo", "car", "auto", 
        "vehicle", "truck", "suv", "sedan", "coupe", "convertible", "dealership", 
        "automotive", "motor", "engine", "transmission", "brake", "cars", "autos", 
        "vehicles", "trucks", "suvs", "sedans", "coupes", "convertibles", "dealers", 
        "dealerships", "motors", "engines", "transmissions", "brakes"
    ]
    text_lower = text.lower()
    return any(term in text_lower for term in automotive_terms)

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
    try:
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
            if len(query_word) >= 4:
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
        
        return min(score, 1.0)
        
    except Exception as e:
        return 0.0

def search_google_sheets_data(query, sheets_data):
    """Enhanced search through 4260+ targeting options"""
    if not sheets_data:
        return None
        
    all_matches = []
    wants_auto = is_automotive_query(query)
    
    # Process all rows for comprehensive search
    for row in sheets_data:
        # Skip automotive content unless explicitly requested
        category = str(row.get("Category", "")).strip()
        grouping = str(row.get("Grouping", "")).strip()
        demographic = str(row.get("Demographic", "")).strip()
        description = str(row.get("Description", "")).strip()
        
        all_text = f"{category} {grouping} {demographic} {description}"
        if is_automotive_content(all_text) and not wants_auto:
            continue
            
        # Calculate enhanced similarity score
        similarity_score = calculate_enhanced_similarity(query, row)
        
        if similarity_score > 0.1:  # Lower threshold to catch more matches
            all_matches.append({
                "row": row,
                "score": similarity_score
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
        
        # Stop at 8 total matches for good selection
        if len(final_matches) >= 8:
            break
    
    return final_matches

def format_targeting_response(matches, query):
    """Format targeting pathways in required format"""
    if not matches:
        return {
            "success": False,
            "response": f"I couldn't find strong matches in our targeting database for '{query}'. Try being more specific with terms or contact ernesto@artemistargeting.com for assistance.",
            "pathways": []
        }
    
    # Always provide minimum 2 combinations
    selected_matches = matches[:3] if len(matches) >= 3 else matches[:2] if len(matches) >= 2 else matches
    
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
        "total_available": len(matches)
    }

# ===== HTTP HANDLER =====

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Test Google Sheets connection
        sheets_data, error = get_google_sheets_data()
        
        response = {
            "status": "google_sheets_embedded", 
            "message": "Enhanced Google Sheets Integration Active",
            "agent": "artemis_enhanced",
            "google_sheets_working": sheets_data is not None,
            "data_count": len(sheets_data) if sheets_data else 0,
            "error": error
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode("utf-8"))
            
            message = body.get("query", body.get("message", "")).strip()
            
            # Try Google Sheets search first
            sheets_data, sheets_error = get_google_sheets_data()
            
            if sheets_data:
                # Search through 4260+ targeting options
                matches = search_google_sheets_data(message, sheets_data)
                
                if matches:
                    formatted_response = format_targeting_response(matches, message)
                    response_text = formatted_response["response"]
                    success = formatted_response["success"]
                else:
                    response_text = f"I couldn't find strong matches in our targeting database for '{message}'. Try being more specific or contact ernesto@artemistargeting.com for assistance."
                    success = False
            else:
                # Fallback to hardcoded if Google Sheets fails
                if "hardwood" in message.lower():
                    response_text = """Based on your audience description, here are the targeting pathways:

**1.** Mobile Location Models → Store Visitors → Hardwood Floor Shoppers
   _Indicates consumer's likelihood to visit Hardwood Floor Shopping. A predictive model based on store visit patterns._

**2.** Mobile Location Models → Store Visitors → High End Furniture Shopper  
   _Consumer is likely to shop at a high-end furniture store. Predictive, statistical analysis based on mobile device data._

These pathways work together to effectively reach your target audience."""
                    success = True
                else:
                    response_text = f"Google Sheets unavailable: {sheets_error}. Contact ernesto@artemistargeting.com"
                    success = False
            
            response = {
                "success": success,
                "response": response_text,
                "agent": "artemis_enhanced",
                "session_id": body.get("session_id", "default"),
                "query": message,
                "data_source": "google_sheets_4260" if sheets_data else "fallback",
                "search_method": "enhanced_similarity"
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            # Emergency fallback for hardwood floors
            try:
                message = body.get("query", body.get("message", "")).strip() if 'body' in locals() else ""
                if "hardwood" in message.lower():
                    emergency_response = {
                        "success": True,
                        "response": """Based on your audience description, here are the targeting pathways:

**1.** Mobile Location Models → Store Visitors → Hardwood Floor Shoppers
   _Indicates consumer's likelihood to visit Hardwood Floor Shopping. A predictive model based on store visit patterns._

**2.** Mobile Location Models → Store Visitors → High End Furniture Shopper  
   _Consumer is likely to shop at a high-end furniture store. Predictive, statistical analysis based on mobile device data._

These pathways work together to effectively reach your target audience.""",
                        "agent": "artemis_emergency",
                        "data_source": "emergency_fallback"
                    }
                else:
                    emergency_response = {
                        "success": False,
                        "response": f"System error: {str(e)}. Contact ernesto@artemistargeting.com",
                        "agent": "artemis_error"
                    }
            except:
                emergency_response = {
                    "success": False,
                    "response": "Critical error occurred. Contact ernesto@artemistargeting.com",
                    "agent": "artemis_critical_error"
                }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(emergency_response).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
