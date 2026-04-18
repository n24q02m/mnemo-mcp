from pathlib import Path

def apply_feedback():
    path = Path("src/mnemo_mcp/db.py")
    lines = path.read_text().splitlines()

    new_lines = []
    skip_until = -1

    for i, line in enumerate(lines):
        if i < skip_until:
            continue

        # 1. Fix _parse_import_data
        if "def _parse_import_data(self, data: str | list | dict) -> tuple[list[dict], int]:" in line:
            new_lines.append(line)
            new_lines.append('        """Parse input data into list of dicts. Returns (items, rejected_count)."""')
            new_lines.append("        rejected = 0")
            new_lines.append("        if isinstance(data, list):")
            new_lines.append("            return data, 0")
            new_lines.append("        if isinstance(data, dict):")
            new_lines.append("            return [data], 0")
            new_lines.append("        if isinstance(data, str):")
            new_lines.append("            data_str = data.strip()")
            new_lines.append("            if not data_str:")
            new_lines.append("                return [], 0")
            new_lines.append("            lines = data_str.splitlines()")
            new_lines.append("            items = []")
            new_lines.append("            for line_item in lines:")
            new_lines.append("                line_item = line_item.strip()")
            new_lines.append("                if not line_item:")
            new_lines.append("                    continue")
            new_lines.append("                try:")
            new_lines.append("                    items.append(json.loads(line_item))")
            new_lines.append("                except Exception:")
            new_lines.append("                    rejected += 1")
            new_lines.append("            return items, rejected")
            new_lines.append("        return [], 0")

            # Find where the old function ends
            for j in range(i + 1, len(lines)):
                if "def _process_import_batch(" in lines[j]:
                    skip_until = j
                    break
            continue

        # 2. Fix _process_import_batch logging
        if "logger.warning(" in line and "import rejected id=" in line:
            new_lines.append(line.replace("logger.warning(", "logger.debug("))
            continue

        new_lines.append(line)

    path.write_text("\n".join(new_lines) + "\n")
    print("Applied PR feedback changes")

if __name__ == "__main__":
    apply_feedback()
