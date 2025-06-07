import os

TARGET_IMPORT = "from mcp.types import ListToolsResult"

def fix_type_checking_blocks(root_dir="."):
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(subdir, file)
                with open(file_path, "r") as f:
                    lines = f.readlines()

                modified = False
                new_lines = []
                inside_type_checking = False
                inserted_import = False

                for i, line in enumerate(lines):
                    stripped = line.strip()

                    if stripped.startswith("if TYPE_CHECKING:"):
                        inside_type_checking = True
                        new_lines.append(line)
                        continue

                    if inside_type_checking:
                        if stripped == "" or stripped.startswith("#"):
                            new_lines.append(line)
                            continue
                        if not line.startswith(" "):
                            if not inserted_import:
                                new_lines.append("    " + TARGET_IMPORT + "\n")
                                inserted_import = True
                                modified = True
                            inside_type_checking = False
                            new_lines.append(line)
                        else:
                            inside_type_checking = False
                            new_lines.append(line)
                    else:
                        new_lines.append(line)

                if inside_type_checking and not inserted_import:
                    new_lines.append("    " + TARGET_IMPORT + "\n")
                    modified = True

                if modified:
                    with open(file_path, "w") as f:
                        f.writelines(new_lines)
                    print(f"✅ Fixed: {file_path}")

if __name__ == "__main__":
    fix_type_checking_blocks("src/mcp_agent")
