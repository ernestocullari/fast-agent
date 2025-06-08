import os

# Define the file path
file_path = 'src/mcp_agent/logger/logger.py'

# Define old and new import lines
old_line = 'from mcp_agent.logging.events import Event, EventContext, EventFilter, EventType'
new_line = 'from mcp_agent.logger.events import Event, EventContext, EventFilter, EventType'

# Ensure the file exists
if not os.path.exists(file_path):
    print(f"❌ File not found: {file_path}")
    exit(1)

# Read and modify the file
with open(file_path, 'r') as f:
    lines = f.readlines()

# Replace the target line
updated_lines = [line.replace(old_line, new_line) for line in lines]

# Write the updated content back
with open(file_path, 'w') as f:
    f.writelines(updated_lines)

print("✅ Import updated successfully in logger.py")

