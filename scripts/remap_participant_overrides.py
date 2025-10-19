#!/usr/bin/env python3
"""Remap participant name overrides to correct match IDs.

When the database is re-imported, match IDs may change. This script
remaps the participant_name_overrides.json file based on player names.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase


def get_match_player_mapping(db: TournamentDatabase) -> dict:
    """Get mapping of (player1, player2) -> match_id.

    Returns normalized player names sorted alphabetically for matching.
    """
    query = """
    SELECT m.match_id, p1.player_name as player1, p2.player_name as player2
    FROM matches m
    JOIN players p1 ON m.match_id = p1.match_id AND p1.player_id = (
        SELECT MIN(player_id) FROM players WHERE match_id = m.match_id
    )
    JOIN players p2 ON m.match_id = p2.match_id AND p2.player_id = (
        SELECT MAX(player_id) FROM players WHERE match_id = m.match_id
    )
    ORDER BY m.match_id
    """

    results = db.fetch_all(query)
    mapping = {}

    for match_id, p1, p2 in results:
        # Sort names alphabetically for consistent matching
        players = tuple(sorted([p1.lower(), p2.lower()]))
        mapping[players] = match_id

    return mapping


def remap_overrides(
    old_overrides: dict,
    db: TournamentDatabase,
    dry_run: bool = False
) -> dict:
    """Remap overrides from old match IDs to new match IDs.

    Args:
        old_overrides: Original overrides dict
        db: Database instance
        dry_run: If True, don't write changes

    Returns:
        New overrides dict with updated match IDs
    """
    # Get current player-to-match mapping
    player_mapping = get_match_player_mapping(db)

    # Get old player-to-match mapping from override file
    # by querying which players are in each override entry
    old_match_players = {}
    for old_match_id_str, players_dict in old_overrides.items():
        if old_match_id_str.startswith("_"):
            continue
        old_match_id = int(old_match_id_str)
        # Get player names from the override
        player_names = list(players_dict.keys())
        old_match_players[old_match_id] = player_names

    print(f"\nRemapping {len(old_match_players)} override entries...")
    print("=" * 70)

    new_overrides = {}
    remapped_count = 0
    not_found_count = 0

    # Copy metadata entries
    for key in old_overrides:
        if key.startswith("_"):
            new_overrides[key] = old_overrides[key]

    # Get all current matches with player names
    all_matches = db.fetch_all("""
        SELECT
            m.match_id,
            GROUP_CONCAT(p.player_name, '|') as players
        FROM matches m
        JOIN players p ON m.match_id = p.match_id
        GROUP BY m.match_id
        ORDER BY m.match_id
    """)

    # Build lookup: set of player names -> match_id
    match_lookup = {}
    for match_id, players_str in all_matches:
        player_names = set(p.lower() for p in players_str.split("|"))
        match_lookup[frozenset(player_names)] = match_id

    # Remap each override entry
    for old_match_id, override_player_names in old_match_players.items():
        # Try to find new match by looking for matching player names
        found = False

        for player_set, new_match_id in match_lookup.items():
            # Check if any override player names match this match
            matches = []
            for override_name in override_player_names:
                if override_name.lower() in player_set:
                    matches.append(override_name)

            # If all override names are in this match, it's a match
            if len(matches) == len(override_player_names):
                # Copy override to new match ID
                new_overrides[str(new_match_id)] = old_overrides[str(old_match_id)]

                player_list = list(player_set)
                print(f"✓ Match {old_match_id:2d} -> {new_match_id:2d}  {override_player_names} in {player_list}")
                remapped_count += 1
                found = True
                break

        if not found:
            print(f"✗ Match {old_match_id:2d} -> ???   {override_player_names} NOT FOUND")
            not_found_count += 1

    print("=" * 70)
    print(f"\nRemapping complete:")
    print(f"  Successfully remapped: {remapped_count}")
    print(f"  Not found: {not_found_count}")

    return new_overrides


def main() -> None:
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Remap participant name overrides")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files"
    )
    args = parser.parse_args()

    overrides_path = Path(Config.PARTICIPANT_NAME_OVERRIDES_PATH)

    if not overrides_path.exists():
        print(f"ERROR: Overrides file not found: {overrides_path}")
        sys.exit(1)

    # Load current overrides
    with open(overrides_path) as f:
        old_overrides = json.load(f)

    print(f"Loaded overrides from: {overrides_path}")

    # Connect to database
    db = TournamentDatabase(Config.DATABASE_PATH, read_only=True)

    # Remap overrides
    new_overrides = remap_overrides(old_overrides, db, dry_run=args.dry_run)

    db.close()

    if args.dry_run:
        print("\n[DRY RUN] Would write updated overrides to:", overrides_path)
        print("\nNew overrides preview:")
        print(json.dumps(new_overrides, indent=2)[:500] + "...")
    else:
        # Backup old file
        backup_path = overrides_path.with_suffix('.json.backup')
        with open(backup_path, 'w') as f:
            json.dump(old_overrides, f, indent=2)
        print(f"\n✓ Backed up old overrides to: {backup_path}")

        # Write new overrides
        with open(overrides_path, 'w') as f:
            json.dump(new_overrides, f, indent=2)
        print(f"✓ Wrote remapped overrides to: {overrides_path}")

        print("\nNext step: Run link_players_to_participants.py")


if __name__ == "__main__":
    main()
