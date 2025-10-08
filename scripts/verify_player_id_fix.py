#!/usr/bin/env python3
"""Verify that MemoryData player ID mapping is fixed."""

from pathlib import Path
from collections import Counter
from tournament_visualizer.data.parser import OldWorldSaveParser


def verify_player_id_mapping(save_file: Path) -> None:
    """Verify player ID mapping for a save file."""
    print(f"Testing: {save_file.name}")
    print("=" * 60)

    parser = OldWorldSaveParser(str(save_file))
    parser.extract_and_parse()

    # Extract both event types
    memory_events = parser.extract_events()
    logdata_events = parser.extract_logdata_events()

    # Count player IDs in MemoryData
    memory_player_counts = Counter(
        e.get('player_id') for e in memory_events
        if e['event_type'].startswith('MEMORYPLAYER_')
    )

    # Count player IDs in LogData
    logdata_player_counts = Counter(
        e.get('player_id') for e in logdata_events
    )

    print("\nMemoryData Player Distribution:")
    for player_id in sorted(memory_player_counts.keys(), key=lambda x: (x is None, x)):
        count = memory_player_counts[player_id]
        print(f"  player_id={player_id}: {count} events")

    print("\nLogData Player Distribution:")
    for player_id in sorted(logdata_player_counts.keys(), key=lambda x: (x is None, x)):
        count = logdata_player_counts[player_id]
        print(f"  player_id={player_id}: {count} events")

    # Validation checks
    print("\nValidation:")

    # Check 1: No player_id=None for MEMORYPLAYER events
    if memory_player_counts.get(None, 0) == 0:
        print("  ✅ No MEMORYPLAYER events with player_id=None")
    else:
        print(f"  ❌ Found {memory_player_counts.get(None, 0)} MEMORYPLAYER events with player_id=None")

    # Check 2: MemoryData and LogData have same player IDs
    memory_ids = set(k for k in memory_player_counts.keys() if k is not None)
    logdata_ids = set(k for k in logdata_player_counts.keys() if k is not None)

    if memory_ids == logdata_ids:
        print(f"  ✅ MemoryData and LogData have same player IDs: {sorted(memory_ids)}")
    else:
        print(f"  ❌ MemoryData IDs {memory_ids} != LogData IDs {logdata_ids}")

    # Check 3: All player IDs are 1-based (1, 2, 3, ...)
    all_ids = memory_ids | logdata_ids
    if all_ids and min(all_ids) >= 1:
        print(f"  ✅ All player IDs are 1-based (min={min(all_ids)})")
    else:
        print(f"  ❌ Player IDs are not 1-based: {sorted(all_ids)}")

    print()


if __name__ == '__main__':
    # Test with all save files in saves/
    saves_dir = Path('saves')
    save_files = list(saves_dir.glob('*.zip'))

    if not save_files:
        print("No save files found in saves/")
        exit(1)

    print(f"Found {len(save_files)} save files to test\n")

    # Test first 3 files (don't need to test all for verification)
    for save_file in save_files[:3]:
        try:
            verify_player_id_mapping(save_file)
        except Exception as e:
            print(f"❌ Error processing {save_file.name}: {e}\n")

    print("Verification complete!")
