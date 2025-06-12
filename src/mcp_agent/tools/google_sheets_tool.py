import os
import asyncio
from typing import Dict, Any, List, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json

from .tool_definition import ToolDefinition


class GoogleSheetsGeotargetingTool:
    """
    Enhanced Google Sheets tool with 4-level search priority for geotargeting data.
    Search order: Description → Demographic → Grouping → Category
    """
    
    def __init__(self):
        self.tool_definition = ToolDefinition(
            name="fetch_geotargeting_tool",
            description="Search geotargeting demographics database with 4-level priority search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "User's plain language description of their target audience"
                    }
                },
                "required": ["query"]
            }
        )
    
    def _get_credentials(self):
        """Initialize Google Sheets API credentials from environment variables."""
        try:
            # Get credentials from environment variables
            client_email = os.getenv('GOOGLE_CLIENT_EMAIL')
            private_key = os.getenv('GOOGLE_PRIVATE_KEY')
            
            if not client_email or not private_key:
                raise ValueError("Missing Google Sheets API credentials in environment variables")
            
            # Replace literal \n with actual newlines in private key
            private_key = private_key.replace('\\n', '\n')
            
            # Create credentials object
            creds_info = {
                "type": "service_account",
                "client_email": client_email,
                "private_key": private_key,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            
            credentials = Credentials.from_service_account_info(
                creds_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
            
            return credentials
            
        except Exception as e:
            raise Exception(f"Failed to initialize Google Sheets credentials: {str(e)}")
    
    def _calculate_match_score(self, text: str, query: str) -> float:
        """Calculate similarity score between text and query."""
        if not text or not query:
            return 0.0
            
        text_lower = text.lower().strip()
        query_lower = query.lower().strip()
        
        # Exact phrase match (highest score)
        if query_lower in text_lower:
            return 100.0
        
        # Word-by-word matching
        query_words = [word for word in query_lower.split() if len(word) > 2]
        if not query_words:
            return 0.0
            
        matched_words = [word for word in query_words if word in text_lower]
        
        if matched_words:
            return (len(matched_words) / len(query_words)) * 80.0
        
        return 0.0
    
    def _search_column(self, data: List[List[str]], column_index: int, column_name: str, 
                      query: str, headers: List[str], min_score: float = 30.0) -> List[Dict]:
        """Search a specific column and return scored matches."""
        matches = []
        
        category_index = self._find_column_index(headers, 'category')
        grouping_index = self._find_column_index(headers, 'grouping')  
        demographic_index = self._find_column_index(headers, 'demographic')
        description_index = self._find_column_index(headers, 'description')
        
        for row_idx, row in enumerate(data):
            if column_index >= len(row):
                continue
                
            cell_value = row[column_index] if column_index < len(row) else ""
            
            if not cell_value.strip():
                continue
                
            score = self._calculate_match_score(cell_value, query)
            
            if score >= min_score:
                matches.append({
                    'category': row[category_index] if category_index < len(row) else "",
                    'grouping': row[grouping_index] if grouping_index < len(row) else "",
                    'demographic': row[demographic_index] if demographic_index < len(row) else "",
                    'description': row[description_index] if description_index < len(row) else "",
                    'matched_text': cell_value,
                    'matched_column': column_name,
                    'score': score,
                    'row_index': row_idx + 2  # +2 because we skip header and use 1-based indexing
                })
        
        return sorted(matches, key=lambda x: x['score'], reverse=True)
    
    def _find_column_index(self, headers: List[str], column_name: str) -> int:
        """Find the index of a column by name (case-insensitive)."""
        for i, header in enumerate(headers):
            if column_name.lower() in header.lower():
                return i
        return -1
    
    async def execute(self, query: str) -> Dict[str, Any]:
        """
        Execute the Google Sheets search with 4-level priority.
        Search order: Description → Demographic → Grouping → Category
        """
        try:
            # Get Google Sheets service
            credentials = self._get_credentials()
            service = build('sheets', 'v4', credentials=credentials)
            
            # Get spreadsheet ID from environment
            spreadsheet_id = os.getenv('GOOGLE_SHEET_ID')
            if not spreadsheet_id:
                return {
                    'success': False,
                    'message': 'GOOGLE_SHEET_ID environment variable not set',
                    'pathways': ''
                }
            
            # Fetch sheet data
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='A:Z'
            ).execute()
            
            rows = result.get('values', [])
            if not rows:
                return {
                    'success': False,
                    'message': 'No data found in the targeting database',
                    'pathways': ''
                }
            
            # Extract headers and data
            headers = rows[0]
            data = rows[1:]  # Skip header row
            
            # Find column indices for required columns
            category_index = self._find_column_index(headers, 'category')
            grouping_index = self._find_column_index(headers, 'grouping')
            demographic_index = self._find_column_index(headers, 'demographic')
            description_index = self._find_column_index(headers, 'description')
            
            # Validate required columns exist
            if any(idx == -1 for idx in [category_index, grouping_index, demographic_index, description_index]):
                return {
                    'success': False,
                    'message': 'Required columns (Category, Grouping, Demographic, Description) not found in sheet',
                    'pathways': ''
                }
            
            # 4-Level Search Priority
            matches = []
            search_source = ""
            
            # STEP 1: Search Description column first (highest priority)
            matches = self._search_column(data, description_index, 'Description', query, headers, 30.0)
            if matches:
                search_source = "Description"
            else:
                # STEP 2: Search Demographic column
                matches = self._search_column(data, demographic_index, 'Demographic', query, headers, 30.0)
                if matches:
                    search_source = "Demographic"
                else:
                    # STEP 3: Search Grouping column
                    matches = self._search_column(data, grouping_index, 'Grouping', query, headers, 30.0)
                    if matches:
                        search_source = "Grouping"
                    else:
                        # STEP 4: Search Category column
                        matches = self._search_column(data, category_index, 'Category', query, headers, 30.0)
                        if matches:
                            search_source = "Category"
            
            # Process results
            if matches:
                # Take top 3 matches
                best_matches = matches[:3]
                
                # Format pathways
                pathways = []
                for i, match in enumerate(best_matches):
                    pathway = f"**Option {i+1}**: {match['category']} → {match['grouping']} → {match['demographic']}"
                    pathways.append(pathway)
                
                # Determine confidence
                top_score = best_matches[0]['score']
                if top_score >= 80:
                    confidence = 'High'
                elif top_score >= 60:
                    confidence = 'Medium'
                else:
                    confidence = 'Low'
                
                return {
                    'success': True,
                    'match_source': search_source.lower(),
                    'message': f'Found {len(best_matches)} targeting pathway(s) by matching "{query}" in the {search_source} column:',
                    'pathways': '\n'.join(pathways),
                    'confidence': confidence,
                    'top_match': {
                        'category': best_matches[0]['category'],
                        'grouping': best_matches[0]['grouping'],
                        'demographic': best_matches[0]['demographic'],
                        'matched_text': best_matches[0]['matched_text'],
                        'searched_in': search_source
                    }
                }
            
            # STEP 5: No matches found
            return {
                'success': True,
                'match_source': 'none',
                'message': f'No targeting pathways found for "{query}" in any column (Description, Demographic, Grouping, or Category).',
                'pathways': '',
                'suggestions': [
                    'Try using different keywords or simpler terms',
                    'Experiment with the targeting tool to explore available options',
                    'Schedule a consultation with ernesto@artemistargeting.com for personalized assistance'
                ],
                'search_attempted': 'Searched all columns: Description, Demographic, Grouping, Category'
            }
            
        except HttpError as e:
            return {
                'success': False,
                'message': f'Google Sheets API error: {str(e)}',
                'pathways': '',
                'suggestions': ['Contact ernesto@artemistargeting.com for technical support']
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Database error: {str(e)}',
                'pathways': '',
                'suggestions': ['Contact ernesto@artemistargeting.com for technical support']
            }


# Create singleton instance
google_sheets_tool = GoogleSheetsGeotargetingTool()
