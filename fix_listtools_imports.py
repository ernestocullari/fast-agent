import os
import re

SRC_DIR = "src/mcp_agent"

def update_imports_in_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    original_content = content

    # Remove TYPE_CHECKING block imports for ListToolsResult
    content = re.sub(
        r"(if TYPE_CHECKING:\s+)([\s\S]*?from\s+mcp\.types\s+import\s+ListToolsResult)",
        lambda m: m.group(1) + "# " + m.group(2).replace("\n", "\n# "),
        content,
        flags=re.MULTILINE,
    )

    # Add or replace runtime import
    if "ListToolsResult" in content and "from mcp.types import ListToolsResult" not in content:
        if "from mcp.types import" in content:
            # Add to existing mcp.types import line
            content = re.sub(
                r"(from\s+mcp\.types\s+import\s+[^\n]+)",
                lambda m: m.group(1).rstrip() + ", ListToolsResult",
                content,
            )
        else:
            # Add new import at top
            content = "from mcp.types import ListToolsResult\n" + content

    if content != original_content:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"Updated: {filepath}")

def walk_project():
    for root, dirs, files in os.walk(SRC_DIR):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                update_imports_in_file(filepath)

if __name__ == "__main__":
    walk_project()
