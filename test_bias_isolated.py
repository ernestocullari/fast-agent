import sys
sys.path.append('src')

# Let's just copy the bias function and test it directly
CATEGORY_BIAS_ADJUSTMENTS = {
    "automotive_categories": ["Automotive", "Auto", "Car", "Vehicle", "Transportation"],
    "automotive_penalty": 0.3,
    "high_priority_categories": [
        "Home & Garden", "Home Improvement", "Real Estate", "Hardware",
        "Health & Fitness", "Wellness", "Medical", "Healthcare",
        "Food & Dining", "Restaurant", "Culinary", "Hospitality",
        "Travel & Tourism", "Hotel", "Vacation", "Leisure",
        "Shopping & Retail", "Fashion", "Beauty", "Lifestyle"
    ],
    "high_priority_boost": 2.5,
    "medium_priority_categories": [
        "Technology", "Finance", "Education", "Entertainment", "Sports"
    ],
    "medium_priority_boost": 1.8,
}

def calculate_category_bias_multiplier(row_data, query):
    """Calculate bias multiplier based on category and query content"""
    category = str(row_data.get("Category", "")).strip()
    grouping = str(row_data.get("Grouping", "")).strip()
    demographic = str(row_data.get("Demographic", "")).strip()
    query_lower = query.lower()
    
    # Check if this is an automotive result
    is_automotive = any(
        auto_cat.lower() in category.lower() or 
        auto_cat.lower() in grouping.lower() or
        auto_cat.lower() in demographic.lower()
        for auto_cat in CATEGORY_BIAS_ADJUSTMENTS["automotive_categories"]
    )
    
    # Check if query explicitly mentions automotive terms
    explicit_automotive_query = any(
        term in query_lower 
        for term in ["car", "auto", "vehicle", "truck", "suv", "bmw", "mercedes", "lexus", "ford", "toyota", "honda", "dealership", "automotive"]
    )
    
    if is_automotive:
        if explicit_automotive_query:
            return 1.0  # No penalty if user explicitly wants automotive
        else:
            return CATEGORY_BIAS_ADJUSTMENTS["automotive_penalty"]  # Heavy penalty for automotive when not requested
    
    # Check for high priority categories
    is_high_priority = any(
        priority_cat.lower() in category.lower() or 
        priority_cat.lower() in grouping.lower()
        for priority_cat in CATEGORY_BIAS_ADJUSTMENTS["high_priority_categories"]
    )
    
    if is_high_priority:
        # Extra boost for home improvement queries
        if any(term in query_lower for term in ["home", "house", "improvement", "renovation", "hardware", "repair"]):
            return CATEGORY_BIAS_ADJUSTMENTS["high_priority_boost"] * 1.5  # Extra boost
        return CATEGORY_BIAS_ADJUSTMENTS["high_priority_boost"]
    
    # Check for medium priority categories
    is_medium_priority = any(
        priority_cat.lower() in category.lower() or 
        priority_cat.lower() in grouping.lower()
        for priority_cat in CATEGORY_BIAS_ADJUSTMENTS["medium_priority_categories"]
    )
    
    if is_medium_priority:
        return CATEGORY_BIAS_ADJUSTMENTS["medium_priority_boost"]
    
    # Default multiplier for other categories
    return 1.2  # Slight boost for non-automotive categories

# Test the function
print("=== TESTING BIAS FUNCTION ===")

# Test 1: Automotive row with home improvement query (should get penalty)
automotive_row = {
    "Category": "Automotive", 
    "Grouping": "In Market for Auto",
    "Demographic": "Acura"
}

home_query = "home improvement customers"
multiplier1 = calculate_category_bias_multiplier(automotive_row, home_query)
print(f"Test 1 - Home query + Automotive row = {multiplier1} (should be 0.3)")

# Test 2: Home row with home improvement query (should get boost)
home_row = {
    "Category": "Home & Garden",
    "Grouping": "Hardware Store", 
    "Demographic": "Home Improvement"
}

multiplier2 = calculate_category_bias_multiplier(home_row, home_query)
print(f"Test 2 - Home query + Home row = {multiplier2} (should be 3.75)")

# Test 3: Automotive row with automotive query (should be normal)
auto_query = "car buyers"
multiplier3 = calculate_category_bias_multiplier(automotive_row, auto_query)
print(f"Test 3 - Auto query + Automotive row = {multiplier3} (should be 1.0)")

# Test calculation example
print(f"\n=== SCORE COMPARISON ===")
base_score = 100
auto_score = base_score * multiplier1  # 100 * 0.3 = 30
home_score = base_score * multiplier2  # 100 * 3.75 = 375
print(f"If both rows had base score of {base_score}:")
print(f"Automotive row final score: {auto_score}")
print(f"Home row final score: {home_score}")
print(f"Home row should win by a large margin!")
