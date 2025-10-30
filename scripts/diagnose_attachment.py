#!/usr/bin/env python3
"""
Diagnostic script to find why a specific attachment URL was not downloaded.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from chyllonge.api import ChallongeApi

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    """Find which match has the attachment and check its status."""
    target_url = "https://user-assets.challonge.com/match_attachments/assets/000/971/876/"

    # Get config
    tournament_id = os.getenv("challonge_tournament_id")
    if not tournament_id:
        print("Error: challonge_tournament_id not set")
        sys.exit(1)

    # Create API client
    api = ChallongeApi()

    # Get all matches
    print(f"Fetching matches from tournament {tournament_id}...")
    matches = api.matches.get_all(tournament_id)
    print(f"Found {len(matches)} total matches\n")

    # Check each match for attachments
    found = False
    for match in matches:
        match_id = match.get("id")
        attachment_count = match.get("attachment_count", 0)

        # Check if this match has attachments
        if not attachment_count or attachment_count == 0:
            continue

        # Get attachments for this match
        try:
            attachments = api.attachments.get_all(tournament_id, match_id)

            for att in attachments:
                asset_url = att.get("asset_url", "")
                if asset_url.startswith("//"):
                    asset_url = "https:" + asset_url

                # Check if this is our target URL
                if "971876" in asset_url or asset_url.startswith(target_url.rstrip("/")):
                    found = True
                    print(f"✓ FOUND ATTACHMENT in match {match_id}")
                    print(f"  URL: {asset_url}")
                    print(f"  Filename: {att.get('asset_file_name', 'N/A')}")
                    print(f"  Size: {att.get('asset_file_size', 'N/A')} bytes")
                    print(f"  Match attachment_count: {attachment_count}")
                    print(f"\n  Full attachment data:")
                    for key, value in att.items():
                        print(f"    {key}: {value}")
                    print()
        except Exception as e:
            print(f"Error fetching attachments for match {match_id}: {e}")

    if not found:
        print(f"❌ Attachment URL not found in any match:")
        print(f"   {target_url}")
        print(f"\nPossible reasons:")
        print(f"  1. Attachment was deleted from Challonge")
        print(f"  2. Attachment belongs to a different tournament")
        print(f"  3. URL format changed")


if __name__ == "__main__":
    main()
