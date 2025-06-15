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

# Enhanced semantic mappings with industry-specific clustering
SEMANTIC_MAPPINGS = {
    # HOME & REAL ESTATE - Comprehensive coverage (HIGH PRIORITY)
    "home improvement": [
        "home renovation",
        "home repair",
        "house renovation",
        "property improvement",
        "home upgrade",
        "remodeling",
    ],
    "home": ["house", "property", "residence", "household", "dwelling"],
    "hardware": ["home improvement", "tools", "building supplies", "construction materials"],
    "flooring": ["hardwood", "carpet", "tile", "laminate", "wood floors", "floor installation"],
    "hardwood": ["wood flooring", "hardwood floors", "wooden floors", "timber flooring"],
    "kitchen": ["kitchen renovation", "kitchen remodel", "culinary", "cooking space"],
    "bathroom": ["bathroom renovation", "bath remodel", "restroom upgrade"],
    "paint": ["painting", "wall paint", "house painting", "interior paint", "exterior paint"],
    "roofing": ["roof repair", "roof replacement", "roofing materials", "shingles"],
    "plumbing": ["plumber", "pipes", "water systems", "drainage"],
    "electrical": ["electrician", "wiring", "electrical work", "lighting"],
    "gardening": ["landscaping", "yard work", "outdoor", "plants", "garden supplies"],
    "real estate": ["property", "home buyers", "house hunting", "property investment"],
    "homeowners": ["property owners", "house owners", "residential owners"],
    
    # AUTOMOTIVE - Detailed and specific (REDUCED PRIORITY)
    "automotive": ["auto", "car", "vehicle", "motor vehicle", "automobile"],
    "car": ["auto", "vehicle", "automobile", "motor vehicle"],
    "luxury car": ["premium vehicle", "high-end car", "luxury auto", "premium automobile"],
    "truck": ["pickup truck", "pickup", "suv", "commercial vehicle"],
    "motorcycle": ["bike", "motorbike", "cruiser", "sport bike", "harley"],
    "bmw": ["luxury german car", "premium bmw", "bavarian motor works"],
    "mercedes": ["luxury car", "premium mercedes", "benz"],
    "lexus": ["luxury japanese car", "premium lexus", "toyota luxury"],
    "ford": ["american car", "ford motor", "f-150"],
    "chevrolet": ["chevy", "american car", "gm vehicle"],
    "auto repair": ["car repair", "vehicle maintenance", "automotive service"],
    "auto parts": ["car parts", "vehicle components", "automotive supplies"],
    "car dealership": ["auto dealer", "vehicle sales", "car sales"],
    "auto insurance": ["car insurance", "vehicle insurance", "automotive coverage"],
    
    # SHOPPING & RETAIL - Behavioral patterns (HIGH PRIORITY)
    "shoppers": ["buyers", "customers", "purchasers", "consumers"],
    "buyers": ["shoppers", "purchasers", "intenders", "customers"],
    "shopping": ["retail", "buying", "purchasing", "consumer behavior"],
    "retail": ["shopping", "store", "commerce", "merchant"],
    "online shopping": ["e-commerce", "digital commerce", "internet shopping"],
    "luxury shopping": ["premium retail", "high-end shopping", "upscale retail"],
    "bargain hunting": ["discount shopping", "deal seeking", "value shopping"],
    "brand loyal": ["brand preference", "repeat customers", "loyal consumers"],
    
    # DEMOGRAPHICS & LIFESTYLE - Broad categories (HIGH PRIORITY)
    "millennials": ["young adults", "gen y", "25-40 years", "digital natives"],
    "gen z": ["young generation", "teens", "digital generation", "18-25 years"],
    "baby boomers": ["seniors", "older adults", "retirement age", "55+ years"],
    "gen x": ["middle aged", "40-55 years", "generation x"],
    "families": ["parents", "households with children", "family units"],
    "parents": ["mothers", "fathers", "caregivers", "family heads"],
    "professionals": ["working professionals", "career oriented", "business people"],
    "students": ["college students", "university", "education", "academic"],
    "retirees": ["seniors", "retirement", "elderly", "senior citizens"],
    
    # INCOME & AFFLUENCE - Economic targeting (HIGH PRIORITY)
    "high income": ["affluent", "wealthy", "upper class", "high earners", "premium income"],
    "affluent": ["wealthy", "high income", "upper income", "prosperous"],
    "wealthy": ["rich", "affluent", "high net worth", "luxury market"],
    "middle class": ["middle income", "average income", "mainstream market"],
    "budget conscious": ["price sensitive", "value seekers", "economical"],
    
    # HEALTH & FITNESS - Wellness market (HIGH PRIORITY)
    "fitness": ["gym", "exercise", "workout", "health club", "athletic"],
    "health": ["wellness", "medical", "healthcare", "fitness"],
    "gym": ["fitness center", "health club", "workout facility"],
    "yoga": ["mindfulness", "meditation", "wellness", "spiritual fitness"],
    "running": ["jogging", "marathon", "athletic", "cardio"],
    "nutrition": ["diet", "healthy eating", "supplements", "wellness"],
    "weight loss": ["diet", "fitness", "health transformation"],
    
    # TRAVEL & HOSPITALITY - Tourism industry (HIGH PRIORITY)
    "travel": ["tourism", "vacation", "holiday", "trip"],
    "hotel": ["accommodation", "lodging", "hospitality", "resort"],
    "vacation": ["holiday", "travel", "leisure trip", "getaway"],
    "business travel": ["corporate travel", "work travel", "business trips"],
    "luxury travel": ["premium travel", "high-end vacation", "luxury resort"],
    "airline": ["flight", "aviation", "air travel"],
    "cruise": ["ship travel", "ocean vacation", "maritime travel"],
    
    # FOOD & DINING - Culinary interests (HIGH PRIORITY)
    "restaurant": ["dining", "food service", "eatery", "cuisine"],
    "coffee": ["cafe", "espresso", "coffee shop", "caffeine"],
    "fine dining": ["upscale restaurant", "gourmet", "luxury dining"],
    "fast food": ["quick service", "casual dining", "convenience food"],
    "organic food": ["natural food", "healthy eating", "organic"],
    "wine": ["alcohol", "beverage", "sommelier", "viticulture"],
    "cooking": ["culinary", "chef", "kitchen", "food preparation"],
    
    # TECHNOLOGY - Digital behavior (MEDIUM PRIORITY)
    "technology": ["tech", "digital", "electronics", "gadgets"],
    "smartphone": ["mobile phone", "cell phone", "device"],
    "gaming": ["video games", "esports", "console", "pc gaming"],
    "software": ["apps", "applications", "digital tools"],
    "social media": ["facebook", "instagram", "twitter", "digital marketing"],
    
    # FASHION & BEAUTY - Style market (MEDIUM PRIORITY)
    "fashion": ["clothing", "apparel", "style", "designer"],
    "beauty": ["cosmetics", "skincare", "makeup", "personal care"],
    "luxury fashion": ["designer clothing", "high fashion", "premium brands"],
    "jewelry": ["accessories", "luxury goods", "precious metals"],
    
    # FINANCIAL SERVICES - Money management (MEDIUM PRIORITY)
    "banking": ["financial services", "finance", "money management"],
    "investment": ["financial planning", "wealth management", "portfolio"],
    "insurance": ["coverage", "protection", "risk management"],
    "loans": ["lending", "credit", "financing", "mortgage"],
    "credit cards": ["payment cards", "credit", "financial products"],
    
    # EDUCATION - Learning market (MEDIUM PRIORITY)
    "education": ["learning", "school", "university", "academic"],
    "online learning": ["e-learning", "digital education", "remote learning"],
    "professional development": ["career advancement", "skill building", "training"],
    
    # INTENT INDICATORS - Purchase behavior (HIGH PRIORITY)
    "in market": ["intenders", "shoppers", "ready to buy", "purchase intent"],
    "intenders": ["in market", "considering purchase", "shopping for"],
    "ready to buy": ["purchase ready", "buying intent", "immediate purchasers"],
    "researching": ["comparison shopping", "investigating", "exploring options"],
    "price comparing": ["deal seeking", "value shopping", "cost conscious"],
}

# Enhanced search scoring with better semantic understanding and automotive bias reduction
SEMANTIC_SCORE_MULTIPLIERS = {
    "exact_phrase": 2.0,  # Exact phrase match in description
    "high_semantic": 1.8,  # Strong semantic relationship
    "medium_semantic": 1.4,  # Moderate semantic relationship
    "low_semantic": 1.1,  # Weak semantic relationship
    "word_match": 1.0,  # Individual word matches
    "category_match": 0.8,  # Category-level matching
}

# Category bias adjustments - NUCLEAR AUTOMOTIVE BIAS PREVENTION
CATEGORY_BIAS_ADJUSTMENTS = {
    # Automotive penalty (NUCLEAR - 99% reduction)
    "automotive_categories": ["Automotive", "Auto", "Car", "Vehicle", "Transportation"],
    "automotive_penalty": 0.01,  # 99% reduction in automotive scores
    
    # Automotive detection terms (comprehensive list)
    "automotive_terms": [
        "acura", "audi", "bmw", "buick", "cadillac", "chevrolet", "chevy", "chrysler",
        "dodge", "ford", "gmc", "honda", "hyundai", "infiniti", "jaguar", "jeep",
        "kia", "lexus", "lincoln", "mazda", "mercedes", "benz", "mitsubishi", "nissan",
        "pontiac", "porsche", "ram", "subaru", "toyota", "volkswagen", "volvo",
        "car", "auto", "vehicle", "truck", "suv", "sedan", "coupe", "convertible",
        "dealership", "automotive", "motor", "engine", "transmission", "brake",
        "tire", "insurance", "lease", "finance", "warranty", "maintenance"
    ],
    
    # High priority categories (MASSIVE boost for non-automotive)
    "high_priority_categories": [
        "Home & Garden", "Home Improvement", "Real Estate", "Hardware",
        "Health & Fitness", "Wellness", "Medical", "Healthcare",
        "Food & Dining", "Restaurant", "Culinary", "Hospitality",
        "Travel & Tourism", "Hotel", "Vacation", "Leisure",
        "Shopping & Retail", "Fashion", "Beauty", "Lifestyle",
    ],
    "high_priority_boost": 10.0,  # 1000% boost for priority categories
    
    # Medium priority categories
    "medium_priority_categories": ["Technology", "Finance", "Education", "Entertainment", "Sports"],
    "medium_priority_boost": 5.0,  # 500% boost for medium categories
}

# Optimized search configuration with enhanced semantic weighting
SEARCH_HIERARCHY = {
    "Description": {"weight": 100, "priority": 1, "threshold": 0.15, "exact_match_bonus": 50},
    "Demographic": {"weight": 75, "priority": 2, "threshold": 0.15, "exact_match_bonus": 25},
    "Grouping": {"weight": 50, "priority": 3, "threshold": 0.15, "exact_match_bonus": 15},
    "Category": {"weight": 25, "priority": 4, "threshold": 0.1, "exact_match_bonus": 10},
}


def calculate_category_bias_multiplier(row_data, query):
    """NUCLEAR FUNCTION: Calculate bias multiplier to eliminate automotive dominance"""
    category = str(row_data.get("Category", "")).strip().lower()
    grouping = str(row_data.get("Grouping", "")).strip().lower()
    demographic = str(row_data.get("Demographic", "")).strip().lower()
    description = str(row_data.get("Description", "")).strip().lower()
    query_lower = query.lower()

    # Check if this is an automotive result (comprehensive detection)
    is_automotive = any(
        auto_cat.lower() in category
        or auto_cat.lower() in grouping
        or auto_cat.lower() in demographic
        for auto_cat in CATEGORY_BIAS_ADJUSTMENTS["automotive_categories"]
    )
    
    # Additional automotive detection by terms in any field
    if not is_automotive:
        all_text = f"{category} {grouping} {demographic} {description}"
        is_automotive = any(
            auto_term in all_text
            for auto_term in CATEGORY_BIAS_ADJUSTMENTS["automotive_terms"]
        )

    # Check if query explicitly mentions automotive terms
    explicit_automotive_query = any(
        term in query_lower
        for term in CATEGORY_BIAS_ADJUSTMENTS["automotive_terms"]
    )

    if is_automotive:
        if explicit_automotive_query:
            return 1.0  # No penalty if user explicitly wants automotive
        else:
            return CATEGORY_BIAS_ADJUSTMENTS["automotive_penalty"]  # NUCLEAR penalty for automotive

    # Check for high priority categories (MASSIVE boost for non-automotive)
    is_high_priority = any(
        priority_cat.lower() in category or priority_cat.lower() in grouping
        for priority_cat in CATEGORY_BIAS_ADJUSTMENTS["high_priority_categories"]
    )

    if is_high_priority:
        # Extra boost for home improvement queries
        if any(
            term in query_lower
            for term in ["home", "house", "improvement", "renovation", "hardware", "repair"]
        ):
            return CATEGORY_BIAS_ADJUSTMENTS["high_priority_boost"] * 1.5  # Extra boost
        return CATEGORY_BIAS_ADJUSTMENTS["high_priority_boost"]

    # Check for medium priority categories
    is_medium_priority = any(
        priority_cat.lower() in category or priority_cat.lower() in grouping
        for priority_cat in CATEGORY_BIAS_ADJUSTMENTS["medium_priority_categories"]
    )

    if is_medium_priority:
        return CATEGORY_BIAS_ADJUSTMENTS["medium_priority_boost"]

    # Default multiplier for other non-automotive categories
    return 2.0  # Good boost for non-automotive categories


class MatchResult:
    def __init__(
        self,
        row,
        column_triggered,
        match_type,
        similarity_score,
        total_score,
        search_term_weight=1.0,
    ):
        self.row = row
        self.column_triggered = column_triggered
        self.match_type = match_type
        self.similarity_score = similarity_score
        self.total_score = total_score * search_term_weight  # Apply semantic weighting
        self.pathway = self._build_pathway()

    def _build_pathway(self):
        category = self.row.get("Category", "")
        grouping = self.row.get("Grouping", "")
        demographic = self.row.get("Demographic", "")
        return f"{category} → {grouping} → {demographic}"


def expand_search_terms(query):
    """Enhanced semantic expansion with relevance scoring and automotive bias reduction"""
    query_lower = query.lower().strip()
    expanded_terms = []

    # Add original query with highest priority
    expanded_terms.append({"term": query_lower, "weight": 2.0, "type": "original"})

    # Enhanced semantic expansion with category awareness
    for key, synonyms in SEMANTIC_MAPPINGS.items():
        if key in query_lower:
            # Reduce weight for automotive terms unless explicitly requested
            base_weight = 1.8
            if key in CATEGORY_BIAS_ADJUSTMENTS["automotive_terms"] and not any(
                auto_term in query_lower
                for auto_term in CATEGORY_BIAS_ADJUSTMENTS["automotive_terms"][:10]  # Top automotive terms
            ):
                base_weight = 0.3  # Heavy reduction for automotive semantic expansion

            # Add the key term itself
            expanded_terms.append({"term": key, "weight": base_weight, "type": "semantic_key"})

            # Add top synonyms with decreasing weights
            for i, synonym in enumerate(synonyms[:4]):  # Limit to top 4 synonyms
                weight = base_weight - 0.2 - (i * 0.1)  # Decreasing weight
                expanded_terms.append(
                    {"term": synonym, "weight": weight, "type": "semantic_synonym"}
                )

    # Individual word expansion with category awareness
    words = query_lower.split()
    for word in words:
        if len(word) > 2:  # Skip very short words
            # Boost non-automotive words
            word_weight = 1.6 if word not in CATEGORY_BIAS_ADJUSTMENTS["automotive_terms"] else 0.2
            expanded_terms.append({"term": word, "weight": word_weight, "type": "word_component"})

            # Check if individual words have semantic mappings
            for key, synonyms in SEMANTIC_MAPPINGS.items():
                if word == key:
                    syn_weight = 1.4 if key not in CATEGORY_BIAS_ADJUSTMENTS["automotive_terms"] else 0.2
                    for synonym in synonyms[:2]:  # Only top 2 for individual words
                        expanded_terms.append(
                            {"term": synonym, "weight": syn_weight, "type": "word_semantic"}
                        )

    # Remove duplicates while preserving highest weight
    seen_terms = {}
    for item in expanded_terms:
        term = item["term"]
        if term not in seen_terms or item["weight"] > seen_terms[term]["weight"]:
            seen_terms[term] = item

    # Sort by weight and return top terms
    final_terms = list(seen_terms.values())
    final_terms.sort(key=lambda x: x["weight"], reverse=True)

    return final_terms[:10]  # Increased to top 10 weighted terms


def calculate_similarity(text1, text2):
    """Enhanced similarity calculation with semantic awareness"""
    if not text1 or not text2:
        return 0.0

    t1_lower = text1.lower()
    t2_lower = text2.lower()

    # Quick exact match check
    if t1_lower == t2_lower:
        return 1.0

    # Enhanced contains check with phrase matching
    if t1_lower in t2_lower:
        # Bonus for longer phrases
        length_bonus = min(len(t1_lower) / 20, 0.2)  # Up to 0.2 bonus for longer matches
        return 0.85 + length_bonus

    if t2_lower in t1_lower:
        length_bonus = min(len(t2_lower) / 20, 0.2)
        return 0.8 + length_bonus

    # Word overlap scoring
    words1 = set(t1_lower.split())
    words2 = set(t2_lower.split())

    if words1 and words2:
        overlap = len(words1.intersection(words2))
        total_words = len(words1.union(words2))
        overlap_score = overlap / total_words

        if overlap_score > 0.2:  # Lowered threshold for better matching
            return 0.4 + (overlap_score * 0.4)

    # Use difflib for remaining cases
    return difflib.SequenceMatcher(None, t1_lower, t2_lower).ratio()


def search_column(expanded_queries, column_text, column_name, config, row, original_query):
    """Enhanced column search with weighted semantic matching and bias correction"""
    if not column_text:
        return []

    column_lower = column_text.lower()
    matches = []

    # Calculate category bias multiplier for this row
    category_multiplier = calculate_category_bias_multiplier(row, original_query)

    for search_item in expanded_queries[:8]:  # Process top 8 weighted terms
        search_term = search_item["term"]
        search_weight = search_item["weight"]
        search_lower = search_term.lower()

        if len(search_lower) < 2:  # Skip very short terms
            continue

        # PRIORITY 1: Exact full match
        if search_lower == column_lower:
            total_score = (
                config["weight"] + config["exact_match_bonus"] + 100
            ) * category_multiplier
            matches.append(
                {
                    "column": column_name,
                    "match_type": "exact_full",
                    "similarity_score": 1.0,
                    "total_score": total_score * search_weight,
                    "search_term": search_term,
                    "search_weight": search_weight,
                    "row": row,
                    "category_multiplier": category_multiplier,
                }
            )
            break  # EARLY EXIT: Found exact match

        # PRIORITY 2: Exact contains match
        elif search_lower in column_lower:
            # Bonus for phrase length and position
            phrase_bonus = min(len(search_lower) / 8, 20)  # Increased bonus
            position_bonus = 15 if column_lower.startswith(search_lower) else 0

            total_score = (
                config["weight"] + config["exact_match_bonus"] + phrase_bonus + position_bonus
            ) * category_multiplier
            matches.append(
                {
                    "column": column_name,
                    "match_type": "exact_contains",
                    "similarity_score": 0.9,
                    "total_score": total_score * search_weight,
                    "search_term": search_term,
                    "search_weight": search_weight,
                    "row": row,
                    "category_multiplier": category_multiplier,
                }
            )

        # PRIORITY 3: Reverse contains (search term contains column text)
        elif column_lower in search_lower:
            total_score = (
                config["weight"] + (config["exact_match_bonus"] * 0.8)
            ) * category_multiplier
            matches.append(
                {
                    "column": column_name,
                    "match_type": "reverse_contains",
                    "similarity_score": 0.85,
                    "total_score": total_score * search_weight,
                    "search_term": search_term,
                    "search_weight": search_weight,
                    "row": row,
                    "category_multiplier": category_multiplier,
                }
            )

        # PRIORITY 4: Enhanced fuzzy match with semantic weighting
        else:
            similarity = calculate_similarity(search_lower, column_lower)
            if similarity >= config["threshold"]:
                # Apply semantic type bonuses
                semantic_bonus = 1.0
                if search_item["type"] in ["semantic_key", "semantic_synonym"]:
                    semantic_bonus = 1.4
                elif search_item["type"] == "original":
                    semantic_bonus = 1.3

                total_score = int(
                    config["weight"] * similarity * semantic_bonus * category_multiplier
                )
                matches.append(
                    {
                        "column": column_name,
                        "match_type": "semantic_fuzzy",
                        "similarity_score": similarity,
                        "total_score": total_score * search_weight,
                        "search_term": search_term,
                        "search_weight": search_weight,
                        "row": row,
                        "category_multiplier": category_multiplier,
                    }
                )

    return matches


def hierarchical_search(query, sheets_data):
    """Enhanced hierarchical search with better semantic matching and bias correction"""
    start_time = time.time()
    expanded_queries = expand_search_terms(query)
    all_matches = []
    processed_rows = 0

    # PERFORMANCE: Process maximum 1000 rows (increased for better coverage)
    max_rows = min(len(sheets_data), 1000)

    for row in sheets_data[:max_rows]:
        processed_rows += 1

        # TIMEOUT CHECK: Every 100 rows
        if processed_rows % 100 == 0:
            if time.time() - start_time > TIMEOUT_SECONDS:
                break

        # EARLY EXIT: Stop after finding 20 good matches (increased for diversity)
        if len(all_matches) >= 20:
            break

        row_matches = []

        # Level 1: Search Description first (highest priority)
        description_matches = search_column(
            expanded_queries,
            str(row.get("Description", "")),
            "Description",
            SEARCH_HIERARCHY["Description"],
            row,
            query,
        )

        # EARLY EXIT: If very high-scoring match found in Description
        excellent_description = [
            m
            for m in description_matches
            if m["match_type"] in ["exact_full", "exact_contains"] and m["total_score"] > 200
        ]
        if excellent_description:
            best_match = max(excellent_description, key=lambda x: x["total_score"])
            match_result = MatchResult(
                row=row,
                column_triggered=best_match["column"],
                match_type=best_match["match_type"],
                similarity_score=best_match["similarity_score"],
                total_score=best_match["total_score"],
                search_term_weight=best_match.get("search_weight", 1.0),
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
            query,
        )
        row_matches.extend(demographic_matches)

        # Level 3: Search Grouping
        grouping_matches = search_column(
            expanded_queries,
            str(row.get("Grouping", "")),
            "Grouping",
            SEARCH_HIERARCHY["Grouping"],
            row,
            query,
        )
        row_matches.extend(grouping_matches)

        # Level 4: Search Category (always include for context)
        category_matches = search_column(
            expanded_queries,
            str(row.get("Category", "")),
            "Category",
            SEARCH_HIERARCHY["Category"],
            row,
            query,
        )
        row_matches.extend(category_matches)

        # Create MatchResult for best match in this row
        if row_matches:
            best_match = max(row_matches, key=lambda x: x["total_score"])
            # Lowered threshold to allow more results through
            if best_match["total_score"] > 1:  # Very low threshold to catch legitimate matches
                match_result = MatchResult(
                    row=row,
                    column_triggered=best_match["column"],
                    match_type=best_match["match_type"],
                    similarity_score=best_match["similarity_score"],
                    total_score=best_match["total_score"],
                    search_term_weight=best_match.get("search_weight", 1.0),
                )
                all_matches.append(match_result)

    # Enhanced sorting with diversity consideration
    all_matches.sort(key=lambda x: x.total_score, reverse=True)

    # Ensure diversity in results - avoid too many from same category
    diverse_matches = []
    seen_categories = {}
    automotive_count = 0
    max_automotive = 0  # START WITH ZERO automotive results

    # Check if automotive was explicitly requested
    automotive_requested = any(
        term in query.lower()
        for term in CATEGORY_BIAS_ADJUSTMENTS["automotive_terms"]
    )

    if automotive_requested:
        max_automotive = 2  # Allow some automotive if explicitly requested

    for match in all_matches:
        category = match.row.get("Category", "")
        category_count = seen_categories.get(category, 0)

        # Check if this is automotive (comprehensive check)
        is_automotive = any(
            auto_cat.lower() in category.lower()
            for auto_cat in CATEGORY_BIAS_ADJUSTMENTS["automotive_categories"]
        ) or any(
            auto_term in f"{category} {match.row.get('Grouping', '')} {match.row.get('Demographic', '')}".lower()
            for auto_term in CATEGORY_BIAS_ADJUSTMENTS["automotive_terms"][:20]  # Check top automotive terms
        )

        # Apply automotive limits (STRICT)
        if is_automotive:
            if automotive_count >= max_automotive:
                continue  # Skip this automotive result
            automotive_count += 1

        # Allow max 2 results per category for diversity (except automotive which is limited above)
        if category_count < 2:
            diverse_matches.append(match)
            seen_categories[category] = category_count + 1

        if len(diverse_matches) >= 8:  # Return top 8 diverse matches
            break

    return diverse_matches


def extract_key_terms(query):
    """Extract meaningful terms from user query for broader search"""
    # Remove common words but keep targeting-relevant terms
    stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an', 'is', 'are', 'was', 'were'}
    words = query.lower().split()
    key_terms = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Prioritize non-automotive terms
    non_automotive_terms = [
        term for term in key_terms 
        if term not in CATEGORY_BIAS_ADJUSTMENTS["automotive_terms"]
    ]
    
    # Return non-automotive terms if available, otherwise return filtered terms
    return non_automotive_terms if non_automotive_terms else key_terms[:3]


def generate_no_match_response(query):
    """Enhanced no-match responses with better suggestions and reduced automotive bias"""
    query_lower = query.lower()
    suggestions = []

    # More specific category detection with non-automotive priorities
    if any(
        word in query_lower
        for word in [
            "home", "house", "property", "improvement", "renovation", "hardware", 
            "flooring", "hardwood", "kitchen", "bathroom", "paint", "roofing"
        ]
    ):
        suggestions = [
            "home improvement shoppers",
            "hardware store visitors", 
            "home renovation intenders",
            "property improvement shoppers",
        ]
    elif any(
        word in query_lower
        for word in ["health", "medical", "fitness", "gym", "wellness", "nutrition", "yoga"]
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
    elif any(word in query_lower for word in ["hotel", "travel", "vacation", "spa", "tourism"]):
        suggestions = [
            "hotel guests",
            "business travelers",
            "vacation planners",
            "luxury travel shoppers",
        ]
    elif any(word in query_lower for word in ["food", "restaurant", "dining", "coffee", "wine"]):
        suggestions = [
            "restaurant visitors",
            "fine dining enthusiasts",
            "coffee shop customers",
            "food enthusiasts",
        ]
    elif any(
        word in query_lower for word in ["technology", "tech", "smartphone", "gaming", "software"]
    ):
        suggestions = [
            "technology enthusiasts",
            "early adopters",
            "gadget shoppers",
            "tech professionals",
        ]
    elif any(word in query_lower for word in ["education", "learning", "student", "university"]):
        suggestions = [
            "education shoppers",
            "online learners",
            "professional development seekers",
            "students",
        ]
    elif any(
        word in query_lower
        for word in CATEGORY_BIAS_ADJUSTMENTS["automotive_terms"]
    ):
        # Only suggest automotive if explicitly requested
        suggestions = [
            "automotive shoppers",
            "luxury car buyers",
            "in market for auto",
            "vehicle intenders",
        ]
    else:
        # Default suggestions - prioritize non-automotive
        suggestions = [
            "high income households",
            "affluent professionals",
            "premium shoppers",
            "home improvement customers",
        ]

    suggestion_text = ", ".join(suggestions)

    return f"""I couldn't find strong matches in our targeting database for '{query}'.

Try being more specific with terms like:
• {suggestion_text}
• Include demographics (age, income, lifestyle)
• Mention specific interests and behaviors

You can also explore our targeting tool or schedule a consultation with ernesto@artemistargeting.com for personalized assistance."""


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

    def search_demographics_with_bias_correction(self, query, query_embedding=None):
        """NEW METHOD: Enhanced search with comprehensive bias correction and fallback logic"""
        start_time = time.time()

        try:
            # Get sheets data (cached)
            sheets_data = self._get_sheets_data()
            if not sheets_data:
                return "I'm unable to access the targeting database right now. Please try again or contact ernesto@artemistargeting.com for assistance."

            # Primary search with bias correction
            matches = hierarchical_search(query, sheets_data)

            if matches:
                # Format and return results
                pathways = []
                seen_pathways = set()
                detailed_matches = []

                for match in matches:
                    if all([match.row["Category"], match.row["Grouping"], match.row["Demographic"]]):
                        pathway = match.pathway
                        if pathway not in seen_pathways:
                            pathways.append(pathway)
                            seen_pathways.add(pathway)
                            detailed_matches.append({
                                "pathway": pathway,
                                "description": match.row.get("Description", ""),
                                "score": match.total_score,
                                "category": match.row.get("Category", ""),
                                "grouping": match.row.get("Grouping", ""),
                                "demographic": match.row.get("Demographic", ""),
                                "match_type": match.match_type,
                                "column_triggered": match.column_triggered,
                            })

                if pathways:
                    return self._format_targeting_response(detailed_matches, query)

            # Fallback: Try with key terms extraction
            key_terms = extract_key_terms(query)
            if key_terms and len(key_terms) != len(query.split()):
                broader_query = " ".join(key_terms)
                fallback_matches = hierarchical_search(broader_query, sheets_data)
                
                if fallback_matches:
                    pathways = []
                    seen_pathways = set()
                    detailed_matches = []

                    for match in fallback_matches[:3]:  # Limit fallback results
                        if all([match.row["Category"], match.row["Grouping"], match.row["Demographic"]]):
                            pathway = match.pathway
                            if pathway not in seen_pathways:
                                pathways.append(pathway)
                                seen_pathways.add(pathway)
                                detailed_matches.append({
                                    "pathway": pathway,
                                    "description": match.row.get("Description", ""),
                                    "score": match.total_score,
                                    "category": match.row.get("Category", ""),
                                    "grouping": match.row.get("Grouping", ""),
                                    "demographic": match.row.get("Demographic", ""),
                                    "match_type": match.match_type,
                                    "column_triggered": match.column_triggered,
                                })

                    if pathways:
                        response = self._format_targeting_response(detailed_matches, query)
                        return f"Based on key terms from your description:\n\n{response}"

            # No matches found
            return generate_no_match_response(query)

        except Exception as e:
            return f"I'm experiencing technical difficulties searching the database. Please try again or contact ernesto@artemistargeting.com for assistance."

    def search_demographics(self, query):
        """Enhanced search with improved semantic matching, bias correction, and response formatting"""
        start_time = time.time()

        try:
            # Check cache first
            cache_key = query.lower().strip()
            if cache_key in SEARCH_CACHE:
                cached_result = SEARCH_CACHE[cache_key].copy()
                cached_result["cache_hit"] = True
                return cached_result

            # Use the new bias-corrected search method
            response_text = self.search_demographics_with_bias_correction(query)

            # Determine success based on response content
            success = not any(phrase in response_text.lower() for phrase in [
                "no specific targeting pathways found",
                "couldn't find strong matches",
                "technical difficulties",
                "unable to access"
            ])

            result = {
                "success": success,
                "response": response_text,  # This is what n8n needs
                "query": query,
                "search_source": "Google Sheets Database - Nuclear Bias Corrected Search",
                "database_search": True,
                "search_method": "nuclear_bias_corrected_hierarchical",
                "response_time": round(time.time() - start_time, 2),
                "cache_hit": False,
            }

            # Cache successful results
            if success and len(SEARCH_CACHE) < CACHE_SIZE_LIMIT:
                SEARCH_CACHE[cache_key] = result.copy()

            return result

        except Exception as e:
            error_response = f"I'm experiencing technical difficulties searching the database. Please try again or contact ernesto@artemistargeting.com for assistance."
            return {
                "success": False,
                "error": f"Database search error: {str(e)}",
                "response": error_response,  # Formatted response for n8n
                "query": query,
                "response_time": round(time.time() - start_time, 2),
            }

    def _format_targeting_response(self, detailed_matches, original_query):
        """Enhanced response formatting with better pathway presentation and bias awareness"""
        if not detailed_matches:
            return generate_no_match_response(original_query)

        response_parts = []
        response_parts.append("Based on your audience description, here are the targeting pathways:\n")

        # Enhanced grouping logic with category diversity emphasis
        if len(detailed_matches) == 1:
            # Single match
            match = detailed_matches[0]
            response_parts.append("🎯 **Primary Targeting:**")
            response_parts.append(f"• {match['pathway']}")
            if match["description"]:
                description = match["description"][:120].strip()
                response_parts.append(f"  _{description}..._")

        elif len(detailed_matches) == 2:
            # Two complementary matches
            response_parts.append("🎯 **Targeting Combination:**")
            for i, match in enumerate(detailed_matches, 1):
                response_parts.append(f"• {match['pathway']}")

            # Add description for the highest scoring match
            best_match = max(detailed_matches, key=lambda x: x["score"])
            if best_match["description"]:
                description = best_match["description"][:100].strip()
                response_parts.append(f"\n_{description}..._")

        else:
            # Multiple matches - prioritize category diversity
            # Group by category for diversity analysis
            category_groups = {}
            for match in detailed_matches:
                category = match["category"]
                if category not in category_groups:
                    category_groups[category] = []
                category_groups[category].append(match)

            # Prioritize non-automotive categories
            automotive_categories = CATEGORY_BIAS_ADJUSTMENTS["automotive_categories"]
            non_automotive_groups = {
                k: v
                for k, v in category_groups.items()
                if not any(auto_cat.lower() in k.lower() for auto_cat in automotive_categories)
            }

            if len(non_automotive_groups) >= 2:
                # Multiple non-automotive categories - show diverse combination
                response_parts.append("🎯 **Targeting Combination:**")
                categories_used = list(non_automotive_groups.keys())[:2]
                for cat in categories_used:
                    best_in_category = max(non_automotive_groups[cat], key=lambda x: x["score"])
                    response_parts.append(f"• {best_in_category['pathway']}")

                # Alternative from remaining matches
                remaining_matches = [
                    m for m in detailed_matches if m["category"] not in categories_used
                ]
                if remaining_matches and len(detailed_matches) > 2:
                    response_parts.append("\n🎯 **Alternative Targeting:**")
                    response_parts.append(f"• {remaining_matches[0]['pathway']}")
            else:
                # Single category or mixed - show top options
                response_parts.append("🎯 **Primary Targeting Options:**")
                for i, match in enumerate(detailed_matches[:3], 1):
                    response_parts.append(f"• {match['pathway']}")

            # Add brief explanation from top non-automotive match if available
            top_non_automotive = None
            for match in detailed_matches:
                if not any(
                    auto_cat.lower() in match["category"].lower()
                    for auto_cat in automotive_categories
                ):
                    top_non_automotive = match
                    break

            explanation_match = top_non_automotive or detailed_matches[0]
            if explanation_match["description"]:
                description = explanation_match["description"][:100].strip()
                response_parts.append(f"\n_{description}..._")

        response_parts.append("\nThese pathways work together to effectively reach your target audience.")

        return "\n".join(response_parts)


# Global instance for the MCP server
sheets_searcher = SheetsSearcher()


def search_sheets_data(query):
    """Main function to be called by the MCP server with enhanced search logic"""
    try:
        # Get embeddings for the query (if needed for future enhancements)
        # For now, we'll use the enhanced hierarchical search
        
        # First attempt: Direct search with bias correction
        result = sheets_searcher.search_demographics(query)
        
        # If no results, try broader search with key terms
        if not result.get("success", False):
            key_terms = extract_key_terms(query)
            if key_terms:
                broader_query = " ".join(key_terms)
                if broader_query != query.lower():
                    fallback_result = sheets_searcher.search_demographics(broader_query)
                    if fallback_result.get("success", False):
                        # Modify response to indicate it's based on key terms
                        response_text = fallback_result.get("response", "")
                        fallback_result["response"] = f"Based on key terms from your description:\n\n{response_text}"
                        return fallback_result
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Search function error: {str(e)}",
            "response": "I'm experiencing technical difficulties. Please try again or contact ernesto@artemistargeting.com for assistance.",
            "query": query,
        }
            "