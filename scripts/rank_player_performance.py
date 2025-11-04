#!/usr/bin/env python3
"""
Rank player performance across all tournament matches.

Analyzes multiple metrics to determine overall player skill and identifies
the best and worst performing players.
"""

import duckdb
import pandas as pd


def calculate_player_rankings(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """
    Calculate comprehensive player performance rankings.

    Metrics:
    - Win Rate: Percentage of games won
    - Avg Victory Points: Average final score
    - Avg Cities: Average cities founded
    - Avg Techs: Average technologies researched
    - Games Played: Total number of tournament games
    """

    query = """
    WITH player_stats AS (
        SELECT
            p.player_name,
            COUNT(*) as games_played,
            SUM(CASE WHEN m.winner_player_id = p.player_id THEN 1 ELSE 0 END) as wins,
            AVG(CASE WHEN ps.turn_number = (SELECT MAX(turn_number) FROM player_statistics ps2 WHERE ps2.match_id = ps.match_id)
                THEN ps.victory_points ELSE NULL END) as avg_victory_points,
            AVG(CASE WHEN ps.turn_number = (SELECT MAX(turn_number) FROM player_statistics ps2 WHERE ps2.match_id = ps.match_id)
                THEN ps.total_cities ELSE NULL END) as avg_cities,
            AVG(CASE WHEN ps.turn_number = (SELECT MAX(turn_number) FROM player_statistics ps2 WHERE ps2.match_id = ps.match_id)
                THEN ps.techs_researched ELSE NULL END) as avg_techs,
            AVG(CASE WHEN ps.turn_number = (SELECT MAX(turn_number) FROM player_statistics ps2 WHERE ps2.match_id = ps.match_id)
                THEN ps.military_strength ELSE NULL END) as avg_military_strength,
            MAX(CASE WHEN ps.turn_number = (SELECT MAX(turn_number) FROM player_statistics ps2 WHERE ps2.match_id = ps.match_id)
                THEN ps.turn_number ELSE NULL END) as avg_game_length
        FROM players p
        JOIN matches m ON p.match_id = m.match_id
        LEFT JOIN player_statistics ps ON p.match_id = ps.match_id AND p.player_id = ps.player_id
        GROUP BY p.player_name
    )
    SELECT
        player_name,
        games_played,
        wins,
        ROUND(CAST(wins AS FLOAT) / games_played * 100, 1) as win_rate_pct,
        ROUND(avg_victory_points, 1) as avg_victory_points,
        ROUND(avg_cities, 1) as avg_cities,
        ROUND(avg_techs, 1) as avg_techs,
        ROUND(avg_military_strength, 1) as avg_military_strength,
        ROUND(avg_game_length, 1) as avg_game_length,
        -- Overall score: weighted combination of win rate (50%), avg victory points (30%), and other metrics (20%)
        ROUND(
            (CAST(wins AS FLOAT) / games_played * 50) +
            (avg_victory_points / 10 * 30) +
            ((avg_cities + avg_techs) / 20 * 20),
            2
        ) as performance_score
    FROM player_stats
    ORDER BY performance_score DESC, win_rate_pct DESC, avg_victory_points DESC
    """

    df = conn.execute(query).df()
    return df


def print_rankings(df: pd.DataFrame) -> None:
    """Print formatted player rankings."""

    print("\n" + "=" * 120)
    print("TOURNAMENT PLAYER PERFORMANCE RANKINGS")
    print("=" * 120)
    print()

    # Add rank column
    df.insert(0, 'Rank', range(1, len(df) + 1))

    # Print table
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 120)
    pd.set_option('display.max_rows', None)

    print(df.to_string(index=False))
    print()

    # Highlight best and worst
    if len(df) > 0:
        print("=" * 120)
        print(f"🏆 BEST PERFORMER: {df.iloc[0]['player_name']}")
        print(f"   - Win Rate: {df.iloc[0]['win_rate_pct']}%")
        print(f"   - Avg Victory Points: {df.iloc[0]['avg_victory_points']}")
        print(f"   - Performance Score: {df.iloc[0]['performance_score']}")
        print()

        if len(df) > 1:
            print(f"⚠️  WORST PERFORMER: {df.iloc[-1]['player_name']}")
            print(f"   - Win Rate: {df.iloc[-1]['win_rate_pct']}%")
            print(f"   - Avg Victory Points: {df.iloc[-1]['avg_victory_points']}")
            print(f"   - Performance Score: {df.iloc[-1]['performance_score']}")
            print()

    print("=" * 120)
    print()
    print("Performance Score = (Win Rate × 50%) + (Avg Victory Points / 10 × 30%) + ((Avg Cities + Avg Techs) / 20 × 20%)")
    print()


def main() -> None:
    """Main entry point."""
    conn = duckdb.connect("data/tournament_data.duckdb", read_only=True)

    print("Calculating player performance rankings...")
    rankings = calculate_player_rankings(conn)

    if rankings.empty:
        print("No player data found in database.")
        return

    print_rankings(rankings)

    # Export to CSV
    output_file = "player_performance_rankings.csv"
    rankings.to_csv(output_file, index=False)
    print(f"Rankings exported to: {output_file}")


if __name__ == "__main__":
    main()
