import os
import json
import re
from googleapiclient.discovery import build
from google.oauth2 import service_account
from difflib import SequenceMatcher


class SheetsSearcher:
    def __init__(self):
        self.service = None
        self.sheet_id = None
        self._setup_sheets_api()

        # Automotive synonyms for better matching
        self.automotive_synonyms = {
            "car": ["auto", "vehicle", "automobile", "automotive"],
            "buyer": ["purchaser", "shopper", "customer", "intender"],
            "luxury": ["premium", "high-end", "upscale", "affluent"],
            "suv": ["utility", "crossover", "truck"],
            "sedan": ["car", "vehicle"],
            "truck": ["pickup", "commercial", "utility"],
            "bmw": ["bavarian", "motor", "works"],
            "mercedes": ["benz", "mb"],
            "audi": ["quattro"],
            "toyota": ["lexus"],
            "honda": ["acura"],
            "ford": ["lincoln"],
            "gm": ["general", "motors", "cadillac", "chevrolet", "buick"],
        }

        # Demographic synonyms
        self.demographic_synonyms = {
            "young": ["millennial", "gen-z", "youth", "adult", "generation"],
            "old": ["senior", "boomer", "elderly", "mature"],
            "rich": ["affluent", "wealthy", "high-income", "premium", "upscale"],
            "parent": ["family", "mother", "father", "household", "mom", "dad"],
            "professional": ["business", "executive", "corporate", "worker", "career"],
            "student": ["college", "university", "education", "academic"],
            "homeowner": ["property", "real estate", "house", "home"],
        }

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
        """Enhanced search with Description column priority and semantic matching"""
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
                return {"error": "No data found in sheet"}

            # Headers are in first row
            headers = values[0]
            data_rows = values[1:]

            # Find column indices
            category_idx = headers.index("Category") if "Category" in headers else 0
            grouping_idx = headers.index("Grouping") if "Grouping" in headers else 1
            demographic_idx = headers.index("Demographic") if "Demographic" in headers else 2
            description_idx = headers.index("Description") if "Description" in headers else 3

            # Enhanced multi-level search with scoring
            all_matches = self._enhanced_search_all_columns(
                data_rows, query, category_idx, grouping_idx, demographic_idx, description_idx
            )

            if all_matches:
                # Sort by total score (highest first)
                all_matches.sort(key=lambda x: x["total_score"], reverse=True)

                # Remove duplicates while preserving order
                seen_pathways = set()
                unique_matches = []
                for match in all_matches:
                    pathway_key = f"{match['row'][category_idx]}-{match['row'][grouping_idx]}-{match['row'][demographic_idx]}"
                    if pathway_key not in seen_pathways:
                        seen_pathways.add(pathway_key)
                        unique_matches.append(match)

                # Format top 3 results as pathways
                pathways = []
                for match in unique_matches[:3]:
                    row = match["row"]
                    pathway = f"{row[category_idx]} → {row[grouping_idx]} → {row[demographic_idx]}"
                    pathways.append(pathway)

                return {
                    "success": True,
                    "pathways": pathways,
                    "search_source": "Enhanced semantic matching",
                    "query": query,
                    "top_score": all_matches[0]["total_score"],
                    "matches_found": len(unique_matches),
                }
            else:
                return {
                    "success": False,
                    "message": f"No matching demographics found for '{query}'. Try describing your audience differently, such as:\n• Age range (young adults, seniors)\n• Income level (affluent, budget-conscious)\n• Interests (automotive, technology, lifestyle)\n• Behaviors (shoppers, buyers, browsers)\n\nFor personalized targeting consultation, contact ernesto@artemistargeting.com",
                    "query": query,
                }

        except Exception as e:
            return {"success": False, "error": f"Error searching demographics: {str(e)}"}

    def _enhanced_search_all_columns(
        self, data_rows, query, category_idx, grouping_idx, demographic_idx, description_idx
    ):
        """Enhanced search across all columns with weighted scoring"""
        matches = []
        query_lower = query.lower()
        query_words = self._extract_keywords(query_lower)

        for row in data_rows:
            if len(row) <= max(category_idx, grouping_idx, demographic_idx, description_idx):
                continue

            category = str(row[category_idx]).lower() if len(row) > category_idx else ""
            grouping = str(row[grouping_idx]).lower() if len(row) > grouping_idx else ""
            demographic = str(row[demographic_idx]).lower() if len(row) > demographic_idx else ""
            description = str(row[description_idx]).lower() if len(row) > description_idx else ""

            # Calculate weighted scores for each column
            description_score = (
                self._calculate_semantic_score(query_lower, description, query_words) * 10
            )  # 10x weight
            demographic_score = (
                self._calculate_semantic_score(query_lower, demographic, query_words) * 5
            )  # 5x weight
            grouping_score = (
                self._calculate_semantic_score(query_lower, grouping, query_words) * 3
            )  # 3x weight
            category_score = (
                self._calculate_semantic_score(query_lower, category, query_words) * 1
            )  # 1x weight

            total_score = description_score + demographic_score + grouping_score + category_score

            # Only include matches with meaningful scores
            if total_score > 3.0:  # Minimum threshold for relevance
                matches.append(
                    {
                        "row": row,
                        "total_score": total_score,
                        "description_score": description_score,
                        "demographic_score": demographic_score,
                        "grouping_score": grouping_score,
                        "category_score": category_score,
                    }
                )

        return matches

    def _calculate_semantic_score(self, query, text, query_words):
        """Calculate semantic similarity score with synonym support"""
        if not text or len(text.strip()) == 0:
            return 0

        score = 0

        # 1. Exact phrase match (highest score)
        if query in text:
            score += 2.0

        # 2. Partial phrase matching
        query_phrases = query.split()
        for phrase in query_phrases:
            if len(phrase) > 2 and phrase in text:
                score += 1.0

        # 3. Individual word matching with synonyms
        text_words = self._extract_keywords(text)
        for query_word in query_words:
            for text_word in text_words:
                # Direct word match
                if query_word in text_word or text_word in query_word:
                    score += 0.5

                # Synonym matching
                if self._are_synonyms(query_word, text_word):
                    score += 0.7

        # 4. Sequence similarity for fuzzy matching
        similarity_ratio = SequenceMatcher(None, query, text).ratio()
        if similarity_ratio > 0.6:
            score += similarity_ratio * 0.5

        # 5. Brand-specific matching for automotive
        if self._has_brand_match(query, text):
            score += 1.5

        return min(score, 3.0)  # Cap maximum score per column

    def _extract_keywords(self, text):
        """Extract meaningful keywords from text"""
        # Remove common stop words and extract meaningful terms
        stop_words = {
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "a",
            "an",
        }
        words = re.findall(r"\b\w+\b", text.lower())
        return [word for word in words if len(word) > 2 and word not in stop_words]

    def _are_synonyms(self, word1, word2):
        """Check if two words are synonyms based on predefined lists"""
        # Check automotive synonyms
        for key, synonyms in self.automotive_synonyms.items():
            if ((word1 == key or word1 in synonyms) and (word2 == key or word2 in synonyms)) or (
                (word2 == key or word2 in synonyms) and (word1 == key or word1 in synonyms)
            ):
                return True

        # Check demographic synonyms
        for key, synonyms in self.demographic_synonyms.items():
            if ((word1 == key or word1 in synonyms) and (word2 == key or word2 in synonyms)) or (
                (word2 == key or word2 in synonyms) and (word1 == key or word1 in synonyms)
            ):
                return True

        return False

    def _has_brand_match(self, query, text):
        """Special handling for automotive brand matching"""
        automotive_brands = [
            "bmw",
            "mercedes",
            "audi",
            "toyota",
            "honda",
            "ford",
            "chevrolet",
            "nissan",
            "volkswagen",
            "hyundai",
            "kia",
            "mazda",
            "subaru",
            "lexus",
            "acura",
            "infiniti",
            "cadillac",
            "lincoln",
            "buick",
            "gmc",
            "ram",
            "jeep",
            "chrysler",
            "dodge",
            "tesla",
            "porsche",
            "jaguar",
            "land rover",
            "volvo",
            "mini",
            "alfa romeo",
            "maserati",
            "bentley",
            "rolls royce",
            "ferrari",
            "lamborghini",
        ]

        query_brands = [brand for brand in automotive_brands if brand in query]
        text_brands = [brand for brand in automotive_brands if brand in text]

        # Check for brand matches
        for qb in query_brands:
            for tb in text_brands:
                if qb == tb or qb in tb or tb in qb:
                    return True

        return False
