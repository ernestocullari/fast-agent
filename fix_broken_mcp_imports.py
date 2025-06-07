import os

PROJECT_ROOT = "src/mcp_agent"

def fix_broken_imports():
    for dirpath, _, filenames in os.walk(PROJECT_ROOT):
        for file in filenames:
            if file.endswith(".py"):
                full_path = os.path.join(dirpath, file)
                with open(full_path, "r") as f:
                    lines = f.readlines()

                modified = False
                new_lines = []
                skip_block = False
                collected_types = []

                for line in lines:
                    if "from mcp.types import (" in line or "from mcp.types import (," in line:
                        skip_block = True
                        collected_types = []
                        modified = True
                        continue

                    if skip_block:
                        if ")" in line:
                            skip_block = False
                            cleaned = [x.strip().strip(",") for x in collected_types if x.strip()]
                            new_lines.append("from mcp.types import (\n")
                            new_lines.extend([f"    {typ},\n" for typ in cleaned])
                            new_lines.append(")\n")
                        else:
                            collected_types.append(line.strip())
                        continue

                    new_lines.append(line)

                if modified:
                    with open(full_path, "w") as f:
                        f.writelines(new_lines)
                    print(f"✅ Fixed import in: {full_path}")

if __name__ == "__main__":
    fix_broken_imports()
