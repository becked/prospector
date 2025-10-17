#!/usr/bin/env python3
"""Investigation script to determine feasibility of GDrive-to-Challonge mapping.

This script:
1. Lists all Challonge matches with player names
2. Compares with known GDrive filenames
3. Attempts to auto-match using player name similarity
4. Reports findings and confidence levels
"""

import os
import re
import sys
from pathlib import Path
from typing import Any

from chyllonge.api import ChallongeApi
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.data.name_normalizer import normalize_name


# Known GDrive files from folder inspection
GDRIVE_FILES = [
    "01-anarkos-becked.zip",
    "02-mojo-fiddler.zip",
    "03-ninja-auro.zip",
    "04-pbm-mongreleyes.zip",
    "05-moroten-droner.zip",
    "06-icematrix-squidleybungo.zip",
    "07-kiriyama-klass_koalas.zip",
    "09-fonder-aran.zip",
    "11-alcaras-rincewind.zip",
    "12-michaelofminsk-amadeus.zip",
    "13-jams-nizar.zip",
    "14-yagman-marauder.zip",
    "15-fiddler-ninja.zip",
    "17-icematrix-kiriyama.zip",
    "19-rincewind-amadeus.zip",
    "21-fluffybunny-becked.zip",
    "24-squidleybungo-klass_koalas.zip",
    "27-alcaras-Michael-of-Minsk.zip",
]


def load_config() -> str:
    """Load tournament ID from environment variables."""
    load_dotenv()

    tournament_id = os.getenv("challonge_tournament_id")
    if not tournament_id:
        raise ValueError("challonge_tournament_id not found in environment variables")

    if not os.getenv("CHALLONGE_KEY"):
        raise ValueError("CHALLONGE_KEY not found in environment variables")

    if not os.getenv("CHALLONGE_USER"):
        raise ValueError("CHALLONGE_USER not found in environment variables")

    return tournament_id


def parse_gdrive_filename(filename: str) -> dict[str, Any]:
    """Parse GDrive filename to extract match info.

    Args:
        filename: Filename like "15-fiddler-ninja.zip"

    Returns:
        Dict with match_number, player1, player2, and normalized names
    """
    match = re.match(r"(\d+)-(.+?)-(.+?)\.zip", filename)
    if not match:
        return {}

    match_num, player1, player2 = match.groups()

    return {
        "match_number": int(match_num),
        "player1": player1,
        "player2": player2,
        "player1_normalized": normalize_name(player1),
        "player2_normalized": normalize_name(player2),
    }


def get_participant_names(
    api: ChallongeApi, tournament_id: str, participant_id: int
) -> str | None:
    """Get display name for a participant."""
    try:
        participants = api.participants.get_all(tournament_id)
        for p in participants:
            if p.get("id") == participant_id:
                return p.get("display_name") or p.get("name")
    except Exception as e:
        print(f"Error fetching participants: {e}")

    return None


def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two names.

    Returns:
        Similarity score from 0.0 (no match) to 1.0 (exact match)
    """
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)

    # Exact match
    if norm1 == norm2:
        return 1.0

    # One is substring of other
    if norm1 in norm2 or norm2 in norm1:
        shorter = min(len(norm1), len(norm2))
        longer = max(len(norm1), len(norm2))
        return shorter / longer

    # No match
    return 0.0


def match_gdrive_to_challonge(
    gdrive_file: str, challonge_matches: list[dict[str, Any]], participants_cache: dict
) -> tuple[int | None, float, str]:
    """Attempt to match a GDrive file to a Challonge match.

    Args:
        gdrive_file: Filename from GDrive
        challonge_matches: List of Challonge match records
        participants_cache: Cache of participant_id -> name

    Returns:
        Tuple of (challonge_match_id, confidence_score, reason)
    """
    gdrive_info = parse_gdrive_filename(gdrive_file)
    if not gdrive_info:
        return None, 0.0, "Failed to parse filename"

    best_match = None
    best_score = 0.0
    best_reason = ""

    for match in challonge_matches:
        # Get participant names
        p1_id = match.get("player1_id")
        p2_id = match.get("player2_id")

        if not p1_id or not p2_id:
            continue

        p1_name = participants_cache.get(p1_id, "")
        p2_name = participants_cache.get(p2_id, "")

        if not p1_name or not p2_name:
            continue

        # Calculate similarity for both orderings
        # GDrive: player1 vs player2
        # Challonge: player1 vs player2
        score1_p1 = calculate_name_similarity(gdrive_info["player1"], p1_name)
        score1_p2 = calculate_name_similarity(gdrive_info["player2"], p2_name)
        score1 = (score1_p1 + score1_p2) / 2

        # GDrive: player1 vs player2
        # Challonge: player2 vs player1 (swapped)
        score2_p1 = calculate_name_similarity(gdrive_info["player1"], p2_name)
        score2_p2 = calculate_name_similarity(gdrive_info["player2"], p1_name)
        score2 = (score2_p1 + score2_p2) / 2

        score = max(score1, score2)

        if score > best_score:
            best_score = score
            best_match = match["id"]
            if score == score1:
                best_reason = f"Matched {gdrive_info['player1']} → {p1_name}, {gdrive_info['player2']} → {p2_name}"
            else:
                best_reason = f"Matched {gdrive_info['player1']} → {p2_name}, {gdrive_info['player2']} → {p1_name}"

    return best_match, best_score, best_reason


def main() -> None:
    """Main investigation function."""
    print("=" * 70)
    print("Google Drive to Challonge Mapping Investigation")
    print("=" * 70)
    print()

    try:
        # Load configuration
        tournament_id = load_config()
        api = ChallongeApi()

        # Fetch Challonge data
        print("Fetching Challonge tournament data...")
        matches = api.matches.get_all(tournament_id)
        participants = api.participants.get_all(tournament_id)

        print(f"  Found {len(matches)} Challonge matches")
        print(f"  Found {len(participants)} participants")
        print()

        # Build participant cache
        participants_cache = {
            p["id"]: p.get("display_name") or p.get("name") for p in participants
        }

        # Check if matches have attachments
        matches_with_attachments = sum(
            1 for m in matches if m.get("attachment_count", 0) > 0
        )
        print(f"Challonge matches with attachments: {matches_with_attachments}")
        print(f"Google Drive files: {len(GDRIVE_FILES)}")
        print()

        # Attempt to match each GDrive file
        print("Attempting to match GDrive files to Challonge matches...")
        print("-" * 70)
        print()

        matched = 0
        high_confidence = 0
        medium_confidence = 0
        low_confidence = 0

        for gdrive_file in GDRIVE_FILES:
            match_id, confidence, reason = match_gdrive_to_challonge(
                gdrive_file, matches, participants_cache
            )

            gdrive_info = parse_gdrive_filename(gdrive_file)
            print(f"GDrive File: {gdrive_file}")
            print(f"  Match #: {gdrive_info['match_number']}")
            print(f"  Players: {gdrive_info['player1']} vs {gdrive_info['player2']}")

            if match_id:
                matched += 1
                print(f"  → Challonge Match ID: {match_id}")
                print(f"  → Confidence: {confidence:.0%}")
                print(f"  → {reason}")

                if confidence >= 0.8:
                    high_confidence += 1
                    print("  ✅ HIGH CONFIDENCE")
                elif confidence >= 0.5:
                    medium_confidence += 1
                    print("  ⚠️  MEDIUM CONFIDENCE - Manual review recommended")
                else:
                    low_confidence += 1
                    print("  ❌ LOW CONFIDENCE - Likely incorrect, needs manual mapping")
            else:
                print("  ❌ NO MATCH FOUND - Manual mapping required")

            print()

        # Summary
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print()
        print(f"Total GDrive files: {len(GDRIVE_FILES)}")
        print(f"Successfully matched: {matched} ({matched/len(GDRIVE_FILES)*100:.0f}%)")
        print()
        print(f"  High confidence (≥80%): {high_confidence}")
        print(f"  Medium confidence (50-80%): {medium_confidence}")
        print(f"  Low confidence (<50%): {low_confidence}")
        print(f"  No match: {len(GDRIVE_FILES) - matched}")
        print()

        # Recommendations
        print("RECOMMENDATIONS:")
        print()

        if high_confidence == len(GDRIVE_FILES):
            print("✅ All files can be auto-matched with high confidence!")
            print("   Proceed with automated mapping script.")
        elif high_confidence + medium_confidence >= len(GDRIVE_FILES) * 0.8:
            print("⚠️  Most files can be auto-matched, but manual review needed.")
            print("   Generate mapping file automatically, then review medium/low confidence matches.")
        else:
            print("❌ Auto-matching has low success rate.")
            print("   Consider manual mapping or investigate alternative approaches:")
            print("   - Use Challonge round/order data")
            print("   - Ask Tournament Organizer for mapping")
            print("   - Use different filename convention going forward")

        print()

        # Check for missing files
        if matches_with_attachments == 0 and len(GDRIVE_FILES) > 0:
            print("📝 NOTE: No Challonge attachments found.")
            print("   Google Drive appears to be the PRIMARY source for save files.")
            print("   Mapping is REQUIRED for system to function.")
        elif matches_with_attachments > 0 and len(GDRIVE_FILES) > 0:
            print("📝 NOTE: Both Challonge and GDrive have files.")
            print("   Investigate which source is authoritative.")
            print("   May need to support both sources (hybrid approach).")

    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
