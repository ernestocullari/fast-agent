import sys
import os
sys.path.append('./src')

from tools.sheets_search import expand_search_terms, SEMANTIC_MAPPINGS

# Test the semantic expansion
query = "home improvement customers"
print(f"Original query: {query}")
print(f"Expanded terms:")

expanded = expand_search_terms(query)
for i, term in enumerate(expanded):
    print(f"  {i+1}. {term}")

print(f"\nSemantic mappings for 'home improvement':")
print(SEMANTIC_MAPPINGS.get("home improvement", "NOT FOUND"))

print(f"\nSemantic mappings for 'home':")
print(SEMANTIC_MAPPINGS.get("home", "NOT FOUND"))
