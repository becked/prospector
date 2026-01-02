#!/usr/bin/env python3
"""Parse Old World tech.xml and generate tech tree data structure."""

import xml.etree.ElementTree as ET


def tech_id_to_display_name(tech_id: str) -> str:
    """Convert TECH_LABOR_FORCE to 'Labor Force'."""
    # Remove TECH_ prefix and convert to title case
    name = tech_id.replace("TECH_", "")
    # Replace underscores with spaces and title case
    return name.replace("_", " ").title()


def parse_tech_tree(xml_path: str) -> tuple[dict[str, tuple[str, int | None, int | None]], list[tuple[str, str]]]:
    """Parse tech.xml and return techs dict and prerequisites list."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    techs: dict[str, tuple[str, int | None, int | None]] = {}
    prerequisites: list[tuple[str, str]] = []

    for entry in root.findall("Entry"):
        z_type = entry.find("zType")
        if z_type is None or not z_type.text:
            continue

        tech_id = z_type.text

        # Get column and row (may be None for bonus techs)
        column_elem = entry.find("iColumn")
        row_elem = entry.find("iRow")

        column: int | None = int(column_elem.text) if (column_elem is not None and column_elem.text) else None
        row: int | None = int(row_elem.text) if (row_elem is not None and row_elem.text) else None

        display_name = tech_id_to_display_name(tech_id)
        techs[tech_id] = (display_name, column, row)

        # Get prerequisites
        prereq_section = entry.find("abTechPrereq")
        if prereq_section is not None:
            for pair in prereq_section.findall("Pair"):
                z_index = pair.find("zIndex")
                if z_index is not None and z_index.text:
                    prereq_id = z_index.text
                    prerequisites.append((prereq_id, tech_id))

    # Second pass: inherit column/row for bonus techs from their parent
    for prereq, unlocks in prerequisites:
        if techs[unlocks][1] is None and prereq in techs:
            parent_col, parent_row = techs[prereq][1], techs[prereq][2]
            if parent_col is not None:
                techs[unlocks] = (techs[unlocks][0], parent_col, parent_row)

    return techs, prerequisites


def generate_output(techs: dict[str, tuple[str, int | None, int | None]], prerequisites: list[tuple[str, str]]) -> str:
    """Generate the Python data structure output."""
    lines = ['"""Old World Tech Tree Data Structure."""', '', 'TECHS = {']
    lines.append('    # id: (display_name, column, row)')

    # Sort by column then row for readability (None values go last)
    def sort_key(item: tuple[str, tuple[str, int | None, int | None]]) -> tuple[int, int, str]:
        tech_id, (_, col, row) = item
        return (col if col is not None else 999, row if row is not None else 999, tech_id)

    sorted_techs = sorted(techs.items(), key=sort_key)

    for tech_id, (display_name, column, row) in sorted_techs:
        lines.append(f'    "{tech_id}": ("{display_name}", {column}, {row}),')

    lines.append('}')
    lines.append('')
    lines.append('# (prerequisite, unlocks)')
    lines.append('PREREQUISITES = [')

    # Sort by prerequisite column then unlocked column
    def prereq_sort_key(prereq_pair: tuple[str, str]) -> tuple[int, int, int, int]:
        p, u = prereq_pair
        p_col = techs[p][1] if techs[p][1] is not None else 999
        p_row = techs[p][2] if techs[p][2] is not None else 999
        u_col = techs[u][1] if techs[u][1] is not None else 999
        u_row = techs[u][2] if techs[u][2] is not None else 999
        return (p_col, p_row, u_col, u_row)

    sorted_prereqs = sorted(prerequisites, key=prereq_sort_key)

    for prereq, unlocks in sorted_prereqs:
        lines.append(f'    ("{prereq}", "{unlocks}"),')

    lines.append(']')

    return '\n'.join(lines)


def main() -> None:
    xml_path = "/Users/jeff/Library/Application Support/Steam/steamapps/common/Old World/Reference/XML/Infos/tech.xml"

    techs, prerequisites = parse_tech_tree(xml_path)

    print(f"Found {len(techs)} techs (including bonus techs)")
    print(f"Found {len(prerequisites)} prerequisite relationships")

    output = generate_output(techs, prerequisites)

    output_path = "/Users/jeff/Projects/Old World/NameEveryChild/tech_tree.py"
    with open(output_path, "w") as f:
        f.write(output)

    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()
