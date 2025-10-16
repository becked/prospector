#!/usr/bin/env python3
"""Example analytics queries using ruler data.

Demonstrates how to analyze ruler archetypes, traits, and succession patterns.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tournament_visualizer.config import Config
from tournament_visualizer.data.database import TournamentDatabase


def archetype_win_rates(db: TournamentDatabase) -> None:
    """Calculate win rates by starting archetype."""
    print("\n" + "=" * 60)
    print("WIN RATES BY STARTING ARCHETYPE")
    print("=" * 60)

    with db.get_connection() as conn:
        results = conn.execute(
            """
            SELECT
                r.archetype,
                COUNT(*) as games,
                SUM(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) as wins,
                ROUND(
                    SUM(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
                    2
                ) as win_rate
            FROM rulers r
            JOIN match_winners mw ON r.match_id = mw.match_id
            WHERE r.succession_order = 0
            AND r.archetype IS NOT NULL
            GROUP BY r.archetype
            ORDER BY win_rate DESC
            """
        ).fetchall()

    print(f"\n{'Archetype':<15} {'Games':<8} {'Wins':<8} {'Win Rate':<10}")
    print("-" * 45)

    for archetype, games, wins, win_rate in results:
        print(f"{archetype:<15} {games:<8} {wins:<8} {win_rate}%")


def trait_win_rates(db: TournamentDatabase) -> None:
    """Calculate win rates by starting trait (top 15)."""
    print("\n" + "=" * 60)
    print("WIN RATES BY STARTING TRAIT (Top 15)")
    print("=" * 60)

    with db.get_connection() as conn:
        results = conn.execute(
            """
            SELECT
                r.starting_trait,
                COUNT(*) as games,
                SUM(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) as wins,
                ROUND(
                    SUM(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
                    2
                ) as win_rate
            FROM rulers r
            JOIN match_winners mw ON r.match_id = mw.match_id
            WHERE r.succession_order = 0
            AND r.starting_trait IS NOT NULL
            GROUP BY r.starting_trait
            HAVING COUNT(*) >= 2
            ORDER BY win_rate DESC
            LIMIT 15
            """
        ).fetchall()

    print(f"\n{'Trait':<20} {'Games':<8} {'Wins':<8} {'Win Rate':<10}")
    print("-" * 50)

    for trait, games, wins, win_rate in results:
        print(f"{trait:<20} {games:<8} {wins:<8} {win_rate}%")


def succession_impact(db: TournamentDatabase) -> None:
    """Analyze relationship between ruler successions and victory."""
    print("\n" + "=" * 60)
    print("SUCCESSION IMPACT ON VICTORY")
    print("=" * 60)

    with db.get_connection() as conn:
        results = conn.execute(
            """
            WITH player_successions AS (
                SELECT
                    r.match_id,
                    r.player_id,
                    COUNT(*) as ruler_count,
                    MAX(CASE WHEN mw.winner_player_id = r.player_id THEN 1 ELSE 0 END) as won
                FROM rulers r
                JOIN match_winners mw ON r.match_id = mw.match_id
                GROUP BY r.match_id, r.player_id
            )
            SELECT
                CASE
                    WHEN ruler_count = 1 THEN '1 ruler'
                    WHEN ruler_count = 2 THEN '2 rulers'
                    WHEN ruler_count = 3 THEN '3 rulers'
                    ELSE '4+ rulers'
                END as succession_count,
                COUNT(*) as games,
                SUM(won) as wins,
                ROUND(SUM(won) * 100.0 / COUNT(*), 2) as win_rate
            FROM player_successions
            GROUP BY
                CASE
                    WHEN ruler_count = 1 THEN '1 ruler'
                    WHEN ruler_count = 2 THEN '2 rulers'
                    WHEN ruler_count = 3 THEN '3 rulers'
                    ELSE '4+ rulers'
                END
            ORDER BY succession_count
            """
        ).fetchall()

    print(f"\n{'Successions':<15} {'Games':<8} {'Wins':<8} {'Win Rate':<10}")
    print("-" * 45)

    for succession, games, wins, win_rate in results:
        print(f"{succession:<15} {games:<8} {wins:<8} {win_rate}%")


def archetype_trait_combinations(db: TournamentDatabase) -> None:
    """Show most common archetype + trait combinations."""
    print("\n" + "=" * 60)
    print("POPULAR ARCHETYPE + TRAIT COMBINATIONS (Top 10)")
    print("=" * 60)

    with db.get_connection() as conn:
        results = conn.execute(
            """
            SELECT
                r.archetype,
                r.starting_trait,
                COUNT(*) as count
            FROM rulers r
            WHERE r.succession_order = 0
            AND r.archetype IS NOT NULL
            AND r.starting_trait IS NOT NULL
            GROUP BY r.archetype, r.starting_trait
            ORDER BY count DESC
            LIMIT 10
            """
        ).fetchall()

    print(f"\n{'Archetype':<15} {'Trait':<20} {'Count':<8}")
    print("-" * 45)

    for archetype, trait, count in results:
        print(f"{archetype:<15} {trait:<20} {count:<8}")


def main() -> None:
    """Run all analytics examples."""
    print("Ruler Analytics Examples")
    print("=" * 60)

    db = TournamentDatabase(Config.DATABASE_PATH)

    # Run analytics
    archetype_win_rates(db)
    trait_win_rates(db)
    succession_impact(db)
    archetype_trait_combinations(db)

    print("\n" + "=" * 60)
    print("Analytics complete!")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    main()
