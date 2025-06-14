import sys
import os
sys.path.append('./src')

from tools.sheets_search import SheetsSearcher

searcher = SheetsSearcher()
result = searcher.search_demographics("home improvement customers")

print("Search result keys:", list(result.keys()))
print("Success:", result.get("success"))
print("Response:", result.get("response", "No response"))
print("Pathways:", result.get("pathways", "No pathways"))
