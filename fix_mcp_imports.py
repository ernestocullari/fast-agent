import os
import re

# Adjust these as needed
search_dir = "src/mcp_agent"
types_symbols = {
    "CallToolResult",
    "EmbeddedResource",
    "GetPromptResult",
    "ImageContent",
    "Prompt",
    "PromptMessage",
    "ReadResourceResult",
    "Role",
    "TextContent",
    "Tool",
    "ListToolsResult",
    "SamplingMessage",
}


def fix_imports_in_file(file_path):
    with open(file_path, "r") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith("from mcp import"):
            matches = re.findall(r"from mcp import (.+)", line)
            if matches:
                imported = [i.strip() for i in matches[0].split(",")]
                from_types = [i for i in imported if i in types_symbols]
                from_mcp = [i for i in imported if i not in types_symbols]

                if from_types:
                    new_lines.append(f"from mcp.types import {', '.join(from_types)}\n")
                if from_mcp:
                    new_lines.append(f"from mcp import {', '.join(from_mcp)}\n")
                continue  # Skip original line
        new_lines.append(line)

    with open(file_path, "w") as f:
        f.writelines(new_lines)


def scan_and_fix():
    for root, _, files in os.walk(search_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                fix_imports_in_file(file_path)
                print(f"✅ Fixed imports in: {file_path}")


if __name__ == "__main__":
    scan_and_fix()
    print("\n🎉 Done! All mcp imports have been split correctly.")
