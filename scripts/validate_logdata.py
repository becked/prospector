#!/usr/bin/env python3
"""Validate LogData import quality by comparing against known values."""

from tournament_visualizer.data.database import get_database
from tournament_visualizer.data.queries import TournamentQueries


def validate_anarkos_becked_match():
    """Validate the anarkos vs becked match has correct law data."""
    db = get_database()

    # Find the anarkos vs becked match
    match_query = """
    SELECT m.match_id
    FROM matches m
    WHERE m.game_name LIKE '%anarkos%becked%'
    """
    with db.get_connection() as conn:
        matches = conn.execute(match_query).df()

    if matches.empty:
        print("❌ Could not find anarkos vs becked match")
        return False

    match_id = int(matches["match_id"].iloc[0])

    # Get law progression
    queries = TournamentQueries(database=db)
    progression = queries.get_law_progression_by_match(match_id)

    # Expected values from manual analysis
    expected = {
        "anarkos": {
            "turn_to_4_laws": 54,
            "turn_to_7_laws": None,  # Never reached 7
            "total_laws": 6,
        },
        "becked": {"turn_to_4_laws": 46, "turn_to_7_laws": 68, "total_laws": 7},
    }

    passed = True
    for _, row in progression.iterrows():
        player = row["player_name"]
        if player not in expected:
            continue

        exp = expected[player]

        # Check turn to 4 laws
        if row["turn_to_4_laws"] != exp["turn_to_4_laws"]:
            print(
                f"❌ {player} turn_to_4_laws: expected {exp['turn_to_4_laws']}, got {row['turn_to_4_laws']}"
            )
            passed = False

        # Check turn to 7 laws
        if pd.isna(row["turn_to_7_laws"]) and exp["turn_to_7_laws"] is not None:
            print(
                f"❌ {player} turn_to_7_laws: expected {exp['turn_to_7_laws']}, got None"
            )
            passed = False
        elif (
            not pd.isna(row["turn_to_7_laws"])
            and row["turn_to_7_laws"] != exp["turn_to_7_laws"]
        ):
            print(
                f"❌ {player} turn_to_7_laws: expected {exp['turn_to_7_laws']}, got {row['turn_to_7_laws']}"
            )
            passed = False

        # Check total laws
        if row["total_laws"] != exp["total_laws"]:
            print(
                f"❌ {player} total_laws: expected {exp['total_laws']}, got {row['total_laws']}"
            )
            passed = False

        if passed:
            print(f"✅ {player} law progression validated")

    return passed


if __name__ == "__main__":
    import pandas as pd

    print("Validating LogData import quality...\n")

    if validate_anarkos_becked_match():
        print("\n✅ All validations passed!")
        exit(0)
    else:
        print("\n❌ Validation failed!")
        exit(1)
