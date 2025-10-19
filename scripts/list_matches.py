#!/usr/bin/env python3
"""
List all matches with player names, civilizations, and URLs.

Usage:
    uv run python scripts/list_matches.py              # Print to screen
    uv run python scripts/list_matches.py --csv        # Write to CSV
    uv run python scripts/list_matches.py --output matches.csv  # Custom filename
"""

import argparse
import csv
import sys
from pathlib import Path

import duckdb


def get_matches(db_path: str) -> list[dict]:
    """Query all matches with player and civilization information."""
    query = """
    WITH numbered_players AS (
        SELECT
            match_id,
            player_name,
            civilization,
            ROW_NUMBER() OVER (PARTITION BY match_id ORDER BY player_id) as player_num
        FROM players
        WHERE is_human = true
    )
    SELECT
        'https://prospector.fly.dev/matches?match_id=' || m.match_id as prospector_url,
        'https://challonge.com/owduels2025/matches/' || m.challonge_match_id || '/share' as challonge_url,
        COALESCE(tp1.display_name, p1.player_name) as player1_name,
        p1.civilization as player1_nation,
        COALESCE(tp2.display_name, p2.player_name) as player2_name,
        p2.civilization as player2_nation
    FROM matches m
    LEFT JOIN tournament_participants tp1 ON m.player1_participant_id = tp1.participant_id
    LEFT JOIN tournament_participants tp2 ON m.player2_participant_id = tp2.participant_id
    LEFT JOIN numbered_players p1 ON m.match_id = p1.match_id AND p1.player_num = 1
    LEFT JOIN numbered_players p2 ON m.match_id = p2.match_id AND p2.player_num = 2
    ORDER BY m.match_id
    """

    conn = duckdb.connect(db_path, read_only=True)
    results = conn.execute(query).fetchall()
    conn.close()

    # Convert to list of dicts
    columns = [
        "prospector_url",
        "challonge_url",
        "player1_name",
        "player1_nation",
        "player2_name",
        "player2_nation",
    ]

    return [dict(zip(columns, row)) for row in results]


def print_matches(matches: list[dict]) -> None:
    """Print matches to stdout in a formatted table."""
    # Print header
    print("┌────────────────────────────────────────────────┬───────────────────────────────────────────────────────────┬────────────────────┬────────────────┬────────────────────┬────────────────┐")
    print("│                 Prospector URL                 │                       Challonge URL                       │    Player 1        │ Player 1 Civ   │    Player 2        │ Player 2 Civ   │")
    print("├────────────────────────────────────────────────┼───────────────────────────────────────────────────────────┼────────────────────┼────────────────┼────────────────────┼────────────────┤")

    # Print rows
    for match in matches:
        print(
            f"│ {match['prospector_url']:<46} │ "
            f"{match['challonge_url']:<57} │ "
            f"{match['player1_name']:<18} │ "
            f"{match['player1_nation']:<14} │ "
            f"{match['player2_name']:<18} │ "
            f"{match['player2_nation']:<14} │"
        )

    # Print footer
    print("└────────────────────────────────────────────────┴───────────────────────────────────────────────────────────┴────────────────────┴────────────────┴────────────────────┴────────────────┘")
    print(f"\n{len(matches)} matches total")


def write_csv(matches: list[dict], output_path: str) -> None:
    """Write matches to a CSV file."""
    if not matches:
        print("No matches to write", file=sys.stderr)
        return

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=matches[0].keys())
        writer.writeheader()
        writer.writerows(matches)

    print(f"Wrote {len(matches)} matches to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List all matches with player names, civilizations, and URLs"
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Write to CSV instead of printing to screen (default: matches.csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output CSV filename (implies --csv)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="data/tournament_data.duckdb",
        help="Path to DuckDB database (default: data/tournament_data.duckdb)",
    )

    args = parser.parse_args()

    # Check if database exists
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    # Get matches
    matches = get_matches(str(db_path))

    # Determine output mode
    if args.output:
        write_csv(matches, args.output)
    elif args.csv:
        write_csv(matches, "matches.csv")
    else:
        print_matches(matches)


if __name__ == "__main__":
    main()
