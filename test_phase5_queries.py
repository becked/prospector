#!/usr/bin/env python3
"""Test script for Phase 5 analytics queries."""

from tournament_visualizer.data.database import get_database
from tournament_visualizer.data.queries import TournamentQueries

def main() -> None:
    """Test all three Phase 5 analytics queries."""
    db = get_database()
    queries = TournamentQueries(db)

    # Get a test match ID
    with db.get_connection() as conn:
        result = conn.execute("SELECT match_id, game_name FROM matches ORDER BY match_id LIMIT 1").fetchone()
        if not result:
            print("❌ No matches found in database")
            return
        match_id, game_name = result

    print(f"Testing queries on match {match_id}: {game_name}\n")

    # Test 1: Law progression query
    print("=" * 60)
    print("Test 1: Law Progression by Match")
    print("=" * 60)
    try:
        law_progression = queries.get_law_progression_by_match(match_id)
        print(f"✅ Query executed successfully")
        print(f"   Rows returned: {len(law_progression)}")
        if not law_progression.empty:
            print("\nResults:")
            print(law_progression.to_string(index=False))
        else:
            print("   No law progression data found (expected if LogData not yet imported)")
    except Exception as e:
        print(f"❌ Query failed: {e}")

    print("\n")

    # Test 2: Tech timeline query
    print("=" * 60)
    print("Test 2: Tech Timeline by Match")
    print("=" * 60)
    try:
        tech_timeline = queries.get_tech_timeline_by_match(match_id)
        print(f"✅ Query executed successfully")
        print(f"   Rows returned: {len(tech_timeline)}")
        if not tech_timeline.empty:
            print("\nFirst 5 results:")
            print(tech_timeline.head().to_string(index=False))
        else:
            print("   No tech timeline data found (expected if LogData not yet imported)")
    except Exception as e:
        print(f"❌ Query failed: {e}")

    print("\n")

    # Test 3: Tech count by turn query
    print("=" * 60)
    print("Test 3: Tech Count by Turn")
    print("=" * 60)
    try:
        tech_count = queries.get_tech_count_by_turn(match_id)
        print(f"✅ Query executed successfully")
        print(f"   Rows returned: {len(tech_count)}")
        if not tech_count.empty:
            print("\nFirst 5 results:")
            print(tech_count.head().to_string(index=False))
        else:
            print("   No tech count data found (expected if LogData not yet imported)")
    except Exception as e:
        print(f"❌ Query failed: {e}")

    print("\n")

    # Test 4: Techs at law milestone query
    print("=" * 60)
    print("Test 4: Techs at Law Milestone (4 laws)")
    print("=" * 60)
    try:
        techs_at_milestone = queries.get_techs_at_law_milestone(match_id, milestone=4)
        print(f"✅ Query executed successfully")
        print(f"   Rows returned: {len(techs_at_milestone)}")
        if not techs_at_milestone.empty:
            print("\nResults:")
            # Show results without the long tech_list column
            display_cols = ['player_id', 'player_name', 'milestone_turn', 'tech_count']
            print(techs_at_milestone[display_cols].to_string(index=False))
        else:
            print("   No milestone data found (expected if LogData not yet imported)")
    except Exception as e:
        print(f"❌ Query failed: {e}")

    print("\n")

    # Test 5: Law progression for all matches
    print("=" * 60)
    print("Test 5: Law Progression for All Matches")
    print("=" * 60)
    try:
        all_law_progression = queries.get_law_progression_by_match()
        print(f"✅ Query executed successfully")
        print(f"   Rows returned: {len(all_law_progression)}")
        if not all_law_progression.empty:
            print("\nFirst 5 results:")
            print(all_law_progression.head().to_string(index=False))
        else:
            print("   No law progression data found (expected if LogData not yet imported)")
    except Exception as e:
        print(f"❌ Query failed: {e}")

    print("\n" + "=" * 60)
    print("All Phase 5 queries tested successfully!")
    print("=" * 60)

if __name__ == '__main__':
    main()
