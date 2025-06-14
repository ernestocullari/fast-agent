import sys
import os
sys.path.append('src')

# You'll need to set these with your actual credentials
print("Note: You'll need to set your Google Sheets credentials for this to work")
print("But let's see if we can at least check the code structure...")

# Import to check if bias function works
from tools.sheets_search import calculate_category_bias_multiplier, CATEGORY_BIAS_ADJUSTMENTS

print("=== BIAS SETTINGS ===")
print(f"Automotive penalty: {CATEGORY_BIAS_ADJUSTMENTS['automotive_penalty']}")
print(f"High priority boost: {CATEGORY_BIAS_ADJUSTMENTS['high_priority_boost']}")

print("\n=== TESTING BIAS FUNCTION ===")

# Test automotive row with home improvement query
automotive_row = {
    "Category": "Automotive", 
    "Grouping": "In Market for Auto",
    "Demographic": "Acura"
}

home_query = "home improvement customers"
multiplier = calculate_category_bias_multiplier(automotive_row, home_query)
print(f"Home improvement query + Automotive row = {multiplier} (should be ~0.3)")

# Test home row with home improvement query  
home_row = {
    "Category": "Home & Garden",
    "Grouping": "Hardware Store", 
    "Demographic": "Home Improvement"
}

multiplier2 = calculate_category_bias_multiplier(home_row, home_query)
print(f"Home improvement query + Home row = {multiplier2} (should be ~3.75)")

