import sys
import os
sys.path.append('src')

# Set up environment variables (you'll need to add your actual values)
os.environ['GOOGLE_CLIENT_EMAIL'] = 'your-service-account@your-project.iam.gserviceaccount.com'
os.environ['GOOGLE_PRIVATE_KEY'] = 'your-private-key-here'
os.environ['GOOGLE_SHEET_ID'] = 'your-sheet-id-here'

from tools.sheets_search import SheetsSearcher

# Test the search
searcher = SheetsSearcher()
result = searcher.search_demographics("home improvement customers")

print("=== DEBUG RESULTS ===")
print(f"Success: {result.get('success')}")
print(f"Query: {result.get('query')}")
print(f"Matches found: {result.get('matches_found', 'N/A')}")

if result.get('success'):
    response = result.get('response', '')
    print("\nResponse:")
    print(response)
else:
    print(f"Error: {result.get('error')}")
    print(f"Response: {result.get('response')}")
