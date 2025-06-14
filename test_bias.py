import sys
sys.path.append('src')
from tools.sheets_search import calculate_category_bias_multiplier

# Test with automotive data
automotive_row = {
    "Category": "Automotive",
    "Grouping": "In Market for Auto (Make)",
    "Demographic": "Acura"
}

# Test with home improvement query
query = "home improvement customers"
multiplier = calculate_category_bias_multiplier(automotive_row, query)

print(f"Query: {query}")
print(f"Row Category: {automotive_row['Category']}")
print(f"Bias Multiplier: {multiplier}")
print(f"Expected: Should be around 0.3 (penalty) for automotive when query is about home improvement")
