#!/usr/bin/env python3
"""Validate all links in README.new.md"""

import re
import sys
from pathlib import Path


def extract_markdown_links(content: str) -> list[tuple[str, str]]:
    """Extract all [text](link) patterns from markdown."""
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    return re.findall(pattern, content)


def validate_links(readme_path: Path) -> int:
    """Validate all links in README.

    Returns:
        Number of broken links found
    """
    content = readme_path.read_text()
    links = extract_markdown_links(content)

    errors = 0
    for text, link in links:
        # Skip external URLs (test manually)
        if link.startswith(('http://', 'https://')):
            print(f"⚠️  External (test manually): {link}")
            continue

        # Skip anchors within same doc
        if link.startswith('#'):
            print(f"ℹ️  Anchor (test manually): {link}")
            continue

        # Handle anchors to other docs
        if '#' in link:
            link_path, anchor = link.split('#', 1)
            target = Path(link_path)
            if not target.exists():
                print(f"✗ BROKEN: {link} (file not found)")
                errors += 1
            else:
                # Just verify file exists, don't validate anchor
                print(f"✓ {link} (file exists)")
        else:
            # Check file/directory exists
            target = Path(link)
            if target.exists():
                print(f"✓ {link}")
            else:
                print(f"✗ BROKEN: {link}")
                errors += 1

    return errors


def main() -> int:
    readme = Path("README.new.md")
    if not readme.exists():
        print(f"Error: {readme} not found")
        return 1

    print(f"Validating links in {readme}...\\n")
    errors = validate_links(readme)

    print(f"\\n{'='*50}")
    if errors > 0:
        print(f"❌ Found {errors} broken links")
        return 1
    else:
        print("✅ All links valid")
        return 0


if __name__ == "__main__":
    sys.exit(main())
