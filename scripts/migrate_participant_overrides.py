#!/usr/bin/env python3
"""Migrate participant_name_overrides.json to use challonge_match_id keys.

This is a ONE-TIME migration script to convert from unstable database match_id
keys to stable challonge_match_id keys.

Usage:
    # Dry run (preview changes)
    python scripts/migrate_participant_overrides.py --dry-run

    # Apply migration
    python scripts/migrate_participant_overrides.py
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config


def load_match_id_mapping(db_path: str) -> dict[int, int]:
    """Load mapping from database match_id to challonge_match_id.

    Args:
        db_path: Path to DuckDB database

    Returns:
        Dict mapping: database match_id → challonge_match_id
    """
    conn = duckdb.connect(db_path, read_only=True)

    try:
        results = conn.execute("""
            SELECT match_id, challonge_match_id
            FROM matches
            WHERE challonge_match_id IS NOT NULL
            ORDER BY match_id
        """).fetchall()

        # Build mapping
        mapping = {match_id: challonge_id for match_id, challonge_id in results}

        print(f"Loaded mapping for {len(mapping)} matches from database")
        return mapping

    finally:
        conn.close()


def migrate_overrides(
    old_overrides: dict,
    match_mapping: dict[int, int],
    dry_run: bool = False
) -> dict:
    """Migrate override keys from match_id to challonge_match_id.

    Args:
        old_overrides: Original overrides dict with match_id keys
        match_mapping: Dict mapping match_id → challonge_match_id
        dry_run: If True, don't write changes

    Returns:
        New overrides dict with challonge_match_id keys
    """
    new_overrides = {}
    migrated_count = 0
    not_found_count = 0

    print("\nMigrating override entries...")
    print("=" * 70)

    # Copy metadata entries (start with underscore)
    for key, value in old_overrides.items():
        if key.startswith("_"):
            new_overrides[key] = value

    # Migrate data entries
    for old_key, players_dict in old_overrides.items():
        if old_key.startswith("_"):
            continue  # Skip metadata

        try:
            # Convert old key (string) to int for lookup
            db_match_id = int(old_key)

            # Look up challonge_match_id
            if db_match_id in match_mapping:
                challonge_match_id = match_mapping[db_match_id]
                new_key = str(challonge_match_id)

                # Copy entry with new key
                new_overrides[new_key] = players_dict

                player_names = list(players_dict.keys())
                print(
                    f"✓ match_id {old_key:>3} → challonge_match_id {new_key:>9}  "
                    f"({len(player_names)} players: {', '.join(player_names)})"
                )
                migrated_count += 1
            else:
                print(
                    f"✗ match_id {old_key:>3} → NOT FOUND in database "
                    f"(match may have been deleted)"
                )
                not_found_count += 1

        except (ValueError, KeyError) as e:
            print(f"✗ Invalid entry '{old_key}': {e}")
            not_found_count += 1

    print("=" * 70)
    print(f"\nMigration summary:")
    print(f"  Successfully migrated: {migrated_count}")
    print(f"  Not found in database: {not_found_count}")
    print(f"  Total entries: {migrated_count + not_found_count}")

    return new_overrides


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Migrate participant overrides to use challonge_match_id"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files"
    )
    args = parser.parse_args()

    overrides_path = Path(Config.PARTICIPANT_NAME_OVERRIDES_PATH)

    if not overrides_path.exists():
        print(f"ERROR: Override file not found: {overrides_path}")
        print("Nothing to migrate.")
        sys.exit(0)

    # Load current overrides
    print(f"Loading overrides from: {overrides_path}")
    with open(overrides_path, "r", encoding="utf-8") as f:
        old_overrides = json.load(f)

    # Load match ID mapping from database
    match_mapping = load_match_id_mapping(Config.DATABASE_PATH)

    # Migrate
    new_overrides = migrate_overrides(old_overrides, match_mapping, args.dry_run)

    if args.dry_run:
        print("\n[DRY RUN] Would write migrated overrides to:", overrides_path)
        print("\nMigrated overrides preview (first 500 chars):")
        preview = json.dumps(new_overrides, indent=2)[:500]
        print(preview + "...")
    else:
        # Backup old file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = overrides_path.with_suffix(f".json.backup_{timestamp}")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(old_overrides, f, indent=2)
        print(f"\n✓ Backed up old overrides to: {backup_path}")

        # Write new overrides
        with open(overrides_path, "w", encoding="utf-8") as f:
            json.dump(new_overrides, f, indent=2)
        print(f"✓ Wrote migrated overrides to: {overrides_path}")

        print("\nNext steps:")
        print("1. Run: uv run python scripts/link_players_to_participants.py")
        print("2. Verify linking worked correctly")
        print("3. Delete: scripts/remap_participant_overrides.py (no longer needed)")
        print("4. Commit the migrated override file")


if __name__ == "__main__":
    main()
