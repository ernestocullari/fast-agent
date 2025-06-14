# Let's manually edit the file with a more targeted approach
with open('src/tools/sheets_search.py', 'r') as f:
    content = f.read()

# Find and replace the specific values
import re

# Replace automotive penalty
content = re.sub(r'"automotive_penalty": [0-9.]+', '"automotive_penalty": 0.01', content)

# Replace high priority boost  
content = re.sub(r'"high_priority_boost": [0-9.]+', '"high_priority_boost": 10.0', content)

# Replace medium priority boost
content = re.sub(r'"medium_priority_boost": [0-9.]+', '"medium_priority_boost": 5.0', content)

# Add sheet-specific categories to high priority list
old_high_priority = '"Home & Garden", "Home Improvement", "Real Estate", "Hardware",'
new_high_priority = '"Home & Garden", "Home Improvement", "Real Estate", "Hardware", "Household Behaviors & Interests", "Household Demographics", "Sports & Recreation",'

content = content.replace(old_high_priority, new_high_priority)

# Write back
with open('src/tools/sheets_search.py', 'w') as f:
    f.write(content)

print("Manual bias fix applied!")
