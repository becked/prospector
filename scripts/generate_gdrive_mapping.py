#!/usr/bin/env python3
"""Generate mapping between Google Drive files and Challonge matches.

This script:
1. Lists files in the Google Drive tournament folder
2. Parses filenames to extract player names
3. Matches files to Challonge matches by player name similarity
4. Outputs a JSON mapping file for use by download script

Usage:
    python scripts/generate_gdrive_mapping.py [--output FILE] [--min-confidence 0.8]
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

from chyllonge.api import ChallongeApi
from dotenv import load_dotenv

# Load environment variables before importing Config
# (Config class variables are evaluated at import time)
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.gdrive_client import GoogleDriveClient
from tournament_visualizer.data.name_normalizer import normalize_name

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def parse_gdrive_filename(filename: str) -> dict[str, Any] | None:
    """Parse Google Drive filename to extract match info.

    Expected format: NN-player1-player2.zip
    Examples:
        - 01-anarkos-becked.zip
        - 15-fiddler-ninja.zip
        - 27-alcaras-Michael-of-Minsk.zip

    Args:
        filename: Google Drive filename

    Returns:
        Dict with match_number, player1, player2, and normalized names.
        None if filename doesn't match expected pattern.
    """
    # Pattern: number-player1-player2.zip
    match = re.match(r"(\d+)-(.+?)-(.+?)\.zip$", filename, re.IGNORECASE)
    if not match:
        return None

    match_num_str, player1, player2 = match.groups()

    return {
        "match_number": int(match_num_str),
        "player1": player1,
        "player2": player2,
        "player1_normalized": normalize_name(player1),
        "player2_normalized": normalize_name(player2),
    }


def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculate similarity score between two names.

    Uses normalized names and checks for exact match or substring match.

    Args:
        name1: First name
        name2: Second name

    Returns:
        Similarity score from 0.0 (no match) to 1.0 (exact match)
    """
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)

    if not norm1 or not norm2:
        return 0.0

    # Exact match
    if norm1 == norm2:
        return 1.0

    # Substring match (one name contains the other)
    if norm1 in norm2 or norm2 in norm1:
        shorter_len = min(len(norm1), len(norm2))
        longer_len = max(len(norm1), len(norm2))
        return shorter_len / longer_len

    return 0.0


def match_gdrive_file_to_challonge(
    gdrive_file: dict[str, Any],
    challonge_matches: list[dict[str, Any]],
    participants: dict[int, str],
) -> tuple[int | None, float, str]:
    """Match a Google Drive file to a Challonge match.

    Uses two strategies in order of preference:
    1. Match by file number if it equals a Challonge match ID (100% confidence)
    2. Match by player name similarity (variable confidence)

    Args:
        gdrive_file: GDrive file metadata with parsed name info
        challonge_matches: List of Challonge match records
        participants: Dict mapping participant_id to display_name

    Returns:
        Tuple of (challonge_match_id, confidence_score, match_reason)
    """
    parsed = parse_gdrive_filename(gdrive_file['name'])
    if not parsed:
        return None, 0.0, "Failed to parse filename"

    # Strategy 1: Try matching by file number prefix
    # Check if the match number corresponds to an actual Challonge match ID
    match_number = parsed['match_number']

    # Build a lookup of Challonge match IDs for fast checking
    challonge_match_ids = {match['id'] for match in challonge_matches}

    if match_number in challonge_match_ids:
        # Validate with player names to ensure it's the right match
        match = next(m for m in challonge_matches if m['id'] == match_number)
        p1_id = match.get('player1_id')
        p2_id = match.get('player2_id')

        if p1_id and p2_id:
            p1_name = participants.get(p1_id, "")
            p2_name = participants.get(p2_id, "")

            # Validate names match (at least partially)
            score1_p1 = calculate_name_similarity(parsed['player1'], p1_name)
            score1_p2 = calculate_name_similarity(parsed['player2'], p2_name)
            score1 = (score1_p1 + score1_p2) / 2

            score2_p1 = calculate_name_similarity(parsed['player1'], p2_name)
            score2_p2 = calculate_name_similarity(parsed['player2'], p1_name)
            score2 = (score2_p1 + score2_p2) / 2

            name_similarity = max(score1, score2)

            # If names match reasonably well (>50%), trust the match number
            if name_similarity > 0.5:
                return (
                    match_number,
                    1.0,  # 100% confidence - match number + validated names
                    f"Matched by file number {match_number} (validated with names)"
                )

    # Strategy 2: Fallback to player name matching
    best_match_id = None
    best_score = 0.0
    best_reason = ""

    for match in challonge_matches:
        p1_id = match.get('player1_id')
        p2_id = match.get('player2_id')

        if not p1_id or not p2_id:
            continue

        p1_name = participants.get(p1_id, "")
        p2_name = participants.get(p2_id, "")

        if not p1_name or not p2_name:
            continue

        # Try both orderings (GDrive player1 vs Challonge player1, and vice versa)
        # Ordering 1: GDrive player1 → Challonge player1
        score1_p1 = calculate_name_similarity(parsed['player1'], p1_name)
        score1_p2 = calculate_name_similarity(parsed['player2'], p2_name)
        score1 = (score1_p1 + score1_p2) / 2

        # Ordering 2: GDrive player1 → Challonge player2 (swapped)
        score2_p1 = calculate_name_similarity(parsed['player1'], p2_name)
        score2_p2 = calculate_name_similarity(parsed['player2'], p1_name)
        score2 = (score2_p1 + score2_p2) / 2

        score = max(score1, score2)

        if score > best_score:
            best_score = score
            best_match_id = match['id']

            if score == score1:
                best_reason = (
                    f"Matched by name similarity: '{parsed['player1']}' → '{p1_name}', "
                    f"'{parsed['player2']}' → '{p2_name}'"
                )
            else:
                best_reason = (
                    f"Matched by name similarity: '{parsed['player1']}' → '{p2_name}', "
                    f"'{parsed['player2']}' → '{p1_name}'"
                )

    return best_match_id, best_score, best_reason


def generate_mapping(
    min_confidence: float = 0.8,
    output_file: Path | None = None,
) -> dict[str, Any]:
    """Generate Google Drive to Challonge match mapping.

    Args:
        min_confidence: Minimum confidence score to include in mapping (0.0-1.0)
        output_file: Path to output JSON file (default: data/gdrive_match_mapping.json)

    Returns:
        Mapping dictionary
    """
    # Initialize clients
    logger.info("Initializing API clients...")
    gdrive_client = GoogleDriveClient(
        api_key=Config.GOOGLE_DRIVE_API_KEY,
        folder_id=Config.GOOGLE_DRIVE_FOLDER_ID,
    )
    challonge_api = ChallongeApi()

    tournament_id = os.getenv("challonge_tournament_id")
    if not tournament_id:
        raise ValueError("challonge_tournament_id not set in environment")

    # Fetch data
    logger.info("Fetching Google Drive files...")
    gdrive_files = gdrive_client.list_files()
    logger.info(f"Found {len(gdrive_files)} files in Google Drive")

    logger.info("Fetching Challonge tournament data...")
    challonge_matches = challonge_api.matches.get_all(tournament_id)
    challonge_participants = challonge_api.participants.get_all(tournament_id)
    logger.info(f"Found {len(challonge_matches)} matches and {len(challonge_participants)} participants")

    # Build participant lookup
    participants = {
        p['id']: p.get('display_name') or p.get('name')
        for p in challonge_participants
    }

    # Match files
    logger.info("Matching Google Drive files to Challonge matches...")
    mapping = {
        "_schema_version": "1.0",
        "_generated_by": "generate_gdrive_mapping.py",
        "_min_confidence": min_confidence,
        "_gdrive_folder_id": Config.GOOGLE_DRIVE_FOLDER_ID,
        "matches": {}
    }

    high_confidence = 0
    medium_confidence = 0
    low_confidence = 0
    unmatched = 0

    for gdrive_file in gdrive_files:
        # Skip non-zip files
        if not gdrive_file['name'].endswith('.zip'):
            logger.debug(f"Skipping non-zip file: {gdrive_file['name']}")
            continue

        match_id, confidence, reason = match_gdrive_file_to_challonge(
            gdrive_file, challonge_matches, participants
        )

        if match_id and confidence >= min_confidence:
            file_size_kb = int(gdrive_file['size']) / 1024

            mapping['matches'][str(match_id)] = {
                "gdrive_file_id": gdrive_file['id'],
                "gdrive_filename": gdrive_file['name'],
                "confidence": round(confidence, 3),
                "match_reason": reason,
                "file_size_kb": round(file_size_kb, 1),
                "modified_time": gdrive_file.get('modifiedTime', ''),
            }

            if confidence >= 0.9:
                status = "✅ HIGH"
                high_confidence += 1
            elif confidence >= 0.8:
                status = "⚠️  MEDIUM"
                medium_confidence += 1
            else:
                status = "❓ LOW"
                low_confidence += 1

            logger.info(
                f"{status} | {gdrive_file['name']} → Match {match_id} "
                f"({confidence:.0%})"
            )
        else:
            unmatched += 1
            if match_id:
                logger.warning(
                    f"❌ SKIPPED | {gdrive_file['name']} → Match {match_id} "
                    f"({confidence:.0%}, below threshold)"
                )
            else:
                logger.warning(f"❌ NO MATCH | {gdrive_file['name']}")

    # Write output
    if output_file is None:
        output_file = Path("data/gdrive_match_mapping.json")

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2)

    logger.info(f"Wrote mapping to {output_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("MAPPING GENERATION SUMMARY")
    print("=" * 70)
    print(f"Total files: {len(gdrive_files)}")
    print(f"Successfully mapped: {len(mapping['matches'])}")
    print(f"  High confidence (≥90%): {high_confidence}")
    print(f"  Medium confidence (80-90%): {medium_confidence}")
    print(f"  Low confidence (below threshold): {low_confidence}")
    print(f"Unmatched: {unmatched}")
    print(f"\nOutput: {output_file}")
    print("=" * 70)

    return mapping


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate Google Drive to Challonge match mapping"
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/gdrive_match_mapping.json"),
        help="Output JSON file path (default: data/gdrive_match_mapping.json)",
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.8,
        help="Minimum confidence score to include (0.0-1.0, default: 0.8)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        generate_mapping(
            min_confidence=args.min_confidence,
            output_file=args.output,
        )
    except Exception as e:
        logger.error(f"Failed to generate mapping: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
