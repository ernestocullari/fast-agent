# Read the current file
with open('src/tools/sheets_search.py', 'r') as f:
    content = f.read()

# Lower the similarity thresholds to help non-automotive data get through
# Change threshold from 0.4 to 0.2 and from 0.3 to 0.1
content = content.replace('"threshold": 0.4', '"threshold": 0.2')
content = content.replace('"threshold": 0.3', '"threshold": 0.1')

# Lower the minimum score threshold from 25 to 5
content = content.replace('if best_match["total_score"] > 25:', 'if best_match["total_score"] > 5:')

# Lower the diversity threshold from 20 to 2
content = content.replace('if best_match["total_score"] > 20:', 'if best_match["total_score"] > 2:')

# Write back
with open('src/tools/sheets_search.py', 'w') as f:
    f.write(content)

print("Balanced nuclear bias:")
print("- Lowered similarity thresholds: 0.4→0.2, 0.3→0.1")
print("- Lowered minimum score: 25→5, 20→2")
print("- This should allow non-automotive data to be found")
