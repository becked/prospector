#!/usr/bin/env python3
"""Verify analytics queries work on full dataset."""

from tournament_visualizer.data.database import get_database
from tournament_visualizer.data.queries import get_queries


def main() -> None:
    db = get_database()
    queries = get_queries()

    # Get all matches
    with db.get_connection() as conn:
        matches = conn.execute("SELECT match_id, game_name FROM matches").df()

    print(f"Testing analytics on {len(matches)} matches...\n")

    for _, match in matches.iterrows():
        match_id = match["match_id"]
        game_name = match["game_name"]

        print(f"Match {match_id}: {game_name}")

        # Test law progression
        try:
            law_prog = queries.get_law_progression_by_match(match_id)
            print(f"  ✅ Law progression: {len(law_prog)} players")
        except Exception as e:
            print(f"  ❌ Law progression failed: {e}")

        # Test tech timeline
        try:
            tech_time = queries.get_tech_timeline_by_match(match_id)
            print(f"  ✅ Tech timeline: {len(tech_time)} discoveries")
        except Exception as e:
            print(f"  ❌ Tech timeline failed: {e}")

        # Test techs at milestone
        try:
            techs_at_4 = queries.get_techs_at_law_milestone(match_id, 4)
            print(f"  ✅ Techs at 4 laws: {len(techs_at_4)} players reached milestone")
        except Exception as e:
            print(f"  ❌ Techs at milestone failed: {e}")

        print()


if __name__ == "__main__":
    main()
