import os
import json
import difflib
from typing import List, Dict, Any
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Universal semantic mappings for all targeting categories
SEMANTIC_MAPPINGS = {
    # Automotive & Transportation
    'car': ['auto', 'vehicle', 'automotive', 'automobile'],
    'luxury car': ['premium vehicle', 'high-end auto', 'luxury auto'],
    'truck': ['pickup', 'suv', 'commercial vehicle'],
    'buyers': ['shoppers', 'intenders', 'purchasers', 'in market'],
    'automotive': ['auto', 'car', 'vehicle', 'transportation'],
    'bmw': ['bmw', 'luxury german car', 'premium auto', 'german luxury'],
    'lexus': ['lexus', 'luxury japanese car', 'premium vehicle', 'japanese luxury'],
    'mercedes': ['mercedes', 'luxury car', 'premium auto', 'german luxury'],
    'toyota': ['toyota', 'japanese car', 'reliable vehicle'],
    'ford': ['ford', 'american car', 'domestic auto'],
    
    # Demographics & Income
    'high income': ['affluent', 'wealthy', 'premium', 'luxury', 'upscale'],
    'middle income': ['middle class', 'moderate income', 'mainstream'],
    'young': ['millennial', 'gen z', 'youth', 'college age', 'young adults'],
    'seniors': ['elderly', 'mature', 'retirement age', 'baby boomers'],
    'families': ['households with children', 'parents', 'family units'],
    
    # Shopping & Retail
    'shopping': ['retail', 'purchasing', 'buying', 'commerce'],
    'online': ['digital', 'e-commerce', 'internet', 'web'],
    'fashion': ['apparel', 'clothing', 'style', 'designer'],
    'electronics': ['tech', 'gadgets', 'devices', 'consumer electronics'],
    
    # Finance & Banking
    'banking': ['financial services', 'finance', 'credit', 'loans'],
    'investing': ['investment', 'wealth management', 'portfolio'],
    'credit': ['lending', 'financing', 'loans', 'mortgages'],
    
    # Healthcare & Wellness
    'health': ['medical', 'healthcare', 'wellness', 'fitness'],
    'beauty': ['cosmetics', 'skincare', 'personal care'],
    'fitness': ['gym', 'exercise', 'workout', 'sports'],
    
    # Real Estate & Home
    'real estate': ['property', 'housing', 'homes', 'residential'],
    'home improvement': ['renovation', 'remodeling', 'diy', 'home repair'],
    'furniture': ['home decor', 'interior design', 'home furnishing'],
    
    # Travel & Hospitality
    'travel': ['tourism', 'vacation', 'hospitality', 'leisure'],
    'hotels': ['accommodation', 'lodging', 'hospitality'],
    'restaurants': ['dining', 'food service', 'culinary'],
    
    # Business & Professional
    'business': ['commercial', 'enterprise', 'corporate', 'professional'],
    'small business': ['smb', 'entrepreneur', 'startup', 'local business'],
    'technology': ['tech', 'software', 'digital', 'it'],
    
    # Intent & Behavior
    'in market': ['intenders', 'shoppers', 'looking to buy', 'ready to purchase'],
    'research': ['considering', 'evaluating', 'comparing', 'browsing'],
    'loyal': ['brand loyal', 'repeat customers', 'brand advocates'],
    'premium': ['luxury', 'high-end', 'upscale', 'exclusive']
}

# Multi-level search configuration - Description has highest priority
SEARCH_HIERARCHY = {
    'Description': {'weight': 100, 'priority': 1, 'threshold': 0.7, 'exact_match_bonus': 50},
    'Demographic': {'weight': 75, 'priority': 2, 'threshold': 0.6, 'exact_match_bonus': 25},
    'Grouping': {'weight': 50, 'priority': 3, 'threshold': 0.6, 'exact_match_bonus': 15},
    'Category': {'weight': 25, 'priority': 4, 'threshold': 0.5, 'exact_match_bonus': 10}
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
        category = self.row.get('Category', '')
        grouping = self.row.get('Grouping', '')
        demographic = self.row.get('Demographic', '')
        return f"{category} → {grouping} → {demographic}"

def expand_search_terms(query):
    """Expand search query with comprehensive semantic mappings"""
    expanded_terms = []
    query_lower = query.lower()
    
    # Add original query
    expanded_terms.append(query)
    
    # Add semantic expansions
    for term, synonyms in SEMANTIC_MAPPINGS.items():
        if term in query_lower:
            expanded_terms.extend(synonyms)
    
    # Add individual words from query for broader matching
    words = query_lower.split()
    expanded_terms.extend(words)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_terms = []
    for term in expanded_terms:
        if term not in seen:
            seen.add(term)
            unique_terms.append(term)
    
    return unique_terms

def calculate_similarity(text1, text2):
    """Calculate similarity score between two text strings"""
    return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def search_column(expanded_queries, column_text, column_name, config, row):
    """Search a specific column with weighted scoring"""
    column_lower = column_text.lower()
    matches = []
    
    for search_term in expanded_queries:
        search_lower = search_term.lower()
        
        # Skip very short terms to avoid false positives
        if len(search_lower) < 2:
            continue
        
        # Exact match check (highest priority)
        if search_lower in column_lower:
            matches.append({
                'column': column_name,
                'match_type': 'exact',
                'similarity_score': 1.0,
                'total_score': config['weight'] + config['exact_match_bonus'],
                'search_term': search_term,
                'row': row
            })
        
        # Fuzzy match check (only for longer terms)
        elif len(search_lower) > 3:
            similarity = calculate_similarity(search_lower, column_lower)
            if similarity >= config['threshold']:
                matches.append({
                    'column': column_name,
                    'match_type': 'fuzzy', 
                    'similarity_score': similarity,
                    'total_score': int(config['weight'] * similarity),
                    'search_term': search_term,
                    'row': row
                })
    
    return matches

def hierarchical_search(query, sheets_data):
    """
    Hierarchical search: Description → Demographic → Grouping → Category
    Returns complete pathways regardless of trigger column
    """
    expanded_queries = expand_search_terms(query)
    all_matches = []
    
    # Search each row against all expanded query terms
    for row in sheets_data:
        row_matches = []
        
        # Level 1: Search Description column first (highest priority)
        description_matches = search_column(
            expanded_queries, 
            str(row.get('Description', '')), 
            'Description',
            SEARCH_HIERARCHY['Description'],
            row
        )
        row_matches.extend(description_matches)
        
        # Level 2: Search Demographic column
        demographic_matches = search_column(
            expanded_queries,
            str(row.get('Demographic', '')),
            'Demographic', 
            SEARCH_HIERARCHY['Demographic'],
            row
        )
        row_matches.extend(demographic_matches)
        
        # Level 3: Search Grouping column
        grouping_matches = search_column(
            expanded_queries,
            str(row.get('Grouping', '')),
            'Grouping',
            SEARCH_HIERARCHY['Grouping'],
            row
        )
        row_matches.extend(grouping_matches)
        
        # Level 4: Search Category column (lowest priority)
        category_matches = search_column(
            expanded_queries,
            str(row.get('Category', '')),
            'Category',
            SEARCH_HIERARCHY['Category'],
            row
        )
        row_matches.extend(category_matches)
        
        # Create MatchResult for best match in this row
        if row_matches:
            best_match = max(row_matches, key=lambda x: x['total_score'])
            match_result = MatchResult(
                row=row,
                column_triggered=best_match['column'],
                match_type=best_match['match_type'],
                similarity_score=best_match['similarity_score'],
                total_score=best_match['total_score']
            )
            all_matches.append(match_result)
    
    # Sort by total score and return top matches
    all_matches.sort(key=lambda x: x.total_score, reverse=True)
    return all_matches[:5]

def format_targeting_response(matches, original_query):
    """Format matches into clean targeting pathways"""
    if not matches:
        return generate_no_match_response(original_query)
    
    response_lines = []
    
    for i, match in enumerate(matches, 1):
        # Always show complete pathway: Category → Grouping → Demographic
        pathway = match.pathway
        
        # Add description for context
        description = match.row.get('Description', '')
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
    if any(word in query_lower for word in ['car', 'auto', 'vehicle', 'bmw', 'lexus']):
        suggestions = ["automotive shoppers", "luxury car buyers", "in market for auto"]
    elif any(word in query_lower for word in ['home', 'house', 'property']):
        suggestions = ["home buyers", "real estate intenders", "property investors"]
    elif any(word in query_lower for word in ['health', 'medical', 'fitness']):
        suggestions = ["health conscious", "fitness enthusiasts", "wellness shoppers"]
    elif any(word in query_lower for word in ['fashion', 'shopping', 'retail']):
        suggestions = ["fashion shoppers", "retail enthusiasts", "online shoppers"]
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
        self._setup_sheets_api()

    def _setup_sheets_api(self):
        """Initialize Google Sheets API with service account credentials"""
        try:
            # Get credentials from environment variables
            client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
            private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")
            self.sheet_id = os.getenv("GOOGLE_SHEET_ID")

            if not all([client_email, private_key, self.sheet_id]):
                raise ValueError("Missing required Google Sheets credentials")

            # Create credentials
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

            # Build service
            self.service = build("sheets", "v4", credentials=credentials)

        except Exception as e:
            print(f"Error setting up Google Sheets API: {e}")
            raise

    def search_demographics(self, query):
        """Enhanced hierarchical search with semantic matching"""
        try:
            # Get sheet data
            sheet = self.service.spreadsheets()
            result = (
                sheet.values()
                .get(
                    spreadsheetId=self.sheet_id,
                    range="A:D",  # Category, Grouping, Demographic, Description
                )
                .execute()
            )

            values = result.get("values", [])
            if not values:
                return {"success": False, "error": "No data found in sheet"}

            # Headers are in first row
            headers = values[0]
            data_rows = values[1:]

            # Find column indices
            try:
                category_idx = headers.index("Category")
                grouping_idx = headers.index("Grouping")
                demographic_idx = headers.index("Demographic")
                description_idx = headers.index("Description")
            except ValueError as e:
                return {"success": False, "error": f"Required column not found: {e}"}

            # Convert rows to dictionary format for hierarchical search
            sheets_data = []
            for row in data_rows:
                if len(row) <= max(category_idx, grouping_idx, demographic_idx, description_idx):
                    continue

                row_dict = {
                    'Category': str(row[category_idx]).strip() if len(row) > category_idx else "",
                    'Grouping': str(row[grouping_idx]).strip() if len(row) > grouping_idx else "",
                    'Demographic': str(row[demographic_idx]).strip() if len(row) > demographic_idx else "",
                    'Description': str(row[description_idx]).strip() if len(row) > description_idx else ""
                }

                # Skip empty rows
                if any([row_dict['Category'], row_dict['Grouping'], row_dict['Demographic'], row_dict['Description']]):
                    sheets_data.append(row_dict)

            # Use hierarchical search
            matches = hierarchical_search(query, sheets_data)

            # Process matches - ONLY return actual database data
            if matches:
                pathways = []
                seen_pathways = set()

                for match in matches:
                    if all([match.row['Category'], match.row['Grouping'], match.row['Demographic']]):
                        pathway = match.pathway
                        if pathway not in seen_pathways:
                            pathways.append(pathway)
                            seen_pathways.add(pathway)
                            if len(pathways) >= 3:  # Max 3 pathways
                                break

                if pathways:
                    return {
                        "success": True,
                        "pathways": pathways,
                        "search_source": "Google Sheets Database - Hierarchical Search",
                        "query": query,
                        "matches_found": len(pathways),
                        "database_search": True,
                        "search_method": "semantic_hierarchical"
                    }

            # NO FABRICATION - Clear failure message when no real matches found
            return {
                "success": False,
                "message": generate_no_match_response(query),
                "query": query,
                "search_attempted": True,
                "database_searched": True,
                "search_method": "semantic_hierarchical"
            }

        except Exception as e:
            return {"success": False, "error": f"Database search error: {str(e)}", "query": query}
