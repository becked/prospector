#!/usr/bin/env python3
"""
Script to list all completed matches without save file attachments.
Uses chyllonge library to interact with the Challonge API.
"""

import json
import sys
from pathlib import Path

from chyllonge.api import ChallongeApi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def load_gdrive_mapping(mapping_path: Path = Path("data/gdrive_match_mapping.json")) -> dict:
    """Load Google Drive match mapping file."""
    if not mapping_path.exists():
        return {"matches": {}}

    try:
        with open(mapping_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading GDrive mapping: {e}")
        return {"matches": {}}


def main() -> None:
    """Main function to list completed matches without saves."""
    # Initialize API
    api = ChallongeApi()

    # Tournament URL
    tournament_url = "owduels2025"

    # Get tournament info
    tournament = api.tournaments.get(tournament_url)
    print(f"Tournament: {tournament['name']}")
    print()

    # Get all matches
    matches = api.matches.get_all(tournament_url)

    # Load Google Drive mapping
    gdrive_mapping = load_gdrive_mapping()
    gdrive_match_ids = set(gdrive_mapping.get("matches", {}).keys())

    # Filter for completed matches without attachments (either on Challonge or GDrive)
    completed_no_saves = []
    for match in matches:
        if match["state"] == "complete":
            match_id_str = str(match["id"])
            attachment_count = match.get("attachment_count", 0)

            # Skip if has Challonge attachment or GDrive mapping
            if attachment_count and attachment_count > 0:
                continue
            if match_id_str in gdrive_match_ids:
                continue

            completed_no_saves.append(match)

    print(f"Completed matches without save files: {len(completed_no_saves)}")
    print()

    # Get participants for name mapping
    participants = api.participants.get_all(tournament_url)
    participant_map = {p["id"]: p["name"] for p in participants}

    # Print details
    for match in completed_no_saves:
        match_id = match["id"]
        round_num = match["round"]
        player1_name = participant_map.get(match["player1_id"], f"ID {match['player1_id']}")
        player2_name = participant_map.get(match["player2_id"], f"ID {match['player2_id']}")

        # Determine bracket
        bracket = "Winners" if round_num > 0 else "Losers"

        print(f"Match ID: {match_id}")
        print(f"  Bracket: {bracket}")
        print(f"  Round: {abs(round_num)}")
        print(f"  Players: {player1_name} vs {player2_name}")
        print(f"  URL: https://challonge.com/{tournament_url}/matches/{match_id}")
        print()


if __name__ == "__main__":
    main()
