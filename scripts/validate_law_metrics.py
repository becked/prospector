"""Validate law metrics across all matches.

This script verifies that the new event-based law counting system
produces sensible results and that all data relationships are correct.
"""

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


def validate_law_metrics() -> None:
    """Check that law metrics make sense."""
    db = TournamentDatabase("data/tournament_data.duckdb")
    queries = TournamentQueries(db)

    print("=" * 60)
    print("Law Metrics Validation")
    print("=" * 60)

    df = queries.get_total_laws_by_player()

    if df.empty:
        print("\n⚠️  WARNING: No law data found!")
        return

    # Validation checks
    issues = []

    print(f"\nTotal players with law data: {len(df)}")

    # 1. Total laws should always be >= unique pairs
    print("\n[1] Validating: total_laws_adopted >= unique_law_pairs...")
    invalid = df[df['total_laws_adopted'] < df['unique_law_pairs']]
    if not invalid.empty:
        issues.append(f"Found {len(invalid)} players with total_laws < unique_pairs")
        print(f"   ❌ FAIL: {len(invalid)} players")
        print("\nInvalid players:")
        print(invalid[['player_name', 'match_id', 'total_laws_adopted', 'unique_law_pairs']])
    else:
        print("   ✅ PASS")

    # 2. Law switches should be non-negative
    print("\n[2] Validating: law_switches >= 0...")
    invalid = df[df['law_switches'] < 0]
    if not invalid.empty:
        issues.append(f"Found {len(invalid)} players with negative law_switches")
        print(f"   ❌ FAIL: {len(invalid)} players")
        print("\nPlayers with negative switches:")
        print(invalid[['player_name', 'match_id', 'law_switches']])
    else:
        print("   ✅ PASS")

    # 3. Check for reasonable values (at least some players should have laws)
    print("\n[3] Validating: at least some players adopted laws...")
    players_with_laws = len(df[df['total_laws_adopted'] > 0])
    if players_with_laws == 0:
        issues.append("No players found with laws adopted")
        print("   ❌ FAIL")
    else:
        print(f"   ✅ PASS ({players_with_laws} players)")

    # 4. Check that unique_law_pairs is not NULL for players with laws
    print("\n[4] Validating: unique_law_pairs is not NULL...")
    null_pairs = df[df['unique_law_pairs'].isna()]
    if not null_pairs.empty:
        issues.append(f"Found {len(null_pairs)} players with NULL unique_law_pairs")
        print(f"   ⚠️  WARNING: {len(null_pairs)} players have NULL unique_law_pairs")
        print("   This may indicate missing data in player_statistics table")
    else:
        print("   ✅ PASS")

    # 5. Report summary stats
    print("\n" + "=" * 60)
    print("Law Metrics Summary")
    print("=" * 60)
    print(f"  Total players analyzed:       {len(df)}")
    print(f"  Players who switched laws:    {(df['law_switches'] > 0).sum()}")
    print(f"  Players with no switches:     {(df['law_switches'] == 0).sum()}")
    print(f"\n  Avg laws adopted per player:  {df['total_laws_adopted'].mean():.2f}")
    print(f"  Avg unique pairs per player:  {df['unique_law_pairs'].mean():.2f}")
    print(f"  Avg switches per player:      {df['law_switches'].mean():.2f}")
    print(f"\n  Max laws adopted (any player): {df['total_laws_adopted'].max()}")
    print(f"  Max switches (any player):     {df['law_switches'].max()}")

    # 6. Show top switchers
    print("\n" + "=" * 60)
    print("Top Law Switchers")
    print("=" * 60)
    top_switchers = df.nlargest(5, 'law_switches')[
        ['player_name', 'match_id', 'total_laws_adopted', 'unique_law_pairs', 'law_switches']
    ]
    if not top_switchers.empty:
        for _, row in top_switchers.iterrows():
            print(f"  {row['player_name']:20} (Match {row['match_id']:2}): "
                  f"{row['total_laws_adopted']} laws, {row['unique_law_pairs']} unique, "
                  f"{row['law_switches']} switches")
    else:
        print("  (none)")

    # 7. Show players with most laws
    print("\n" + "=" * 60)
    print("Most Laws Adopted")
    print("=" * 60)
    top_lawmakers = df.nlargest(5, 'total_laws_adopted')[
        ['player_name', 'match_id', 'total_laws_adopted', 'unique_law_pairs', 'law_switches']
    ]
    for _, row in top_lawmakers.iterrows():
        print(f"  {row['player_name']:20} (Match {row['match_id']:2}): "
              f"{row['total_laws_adopted']} laws, {row['unique_law_pairs']} unique, "
              f"{row['law_switches']} switches")

    # Final result
    print("\n" + "=" * 60)
    if issues:
        print("❌ VALIDATION FAILED")
        print("=" * 60)
        print("\nIssues found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nPlease investigate these issues before proceeding.")
        exit(1)
    else:
        print("✅ ALL VALIDATIONS PASSED")
        print("=" * 60)
        print("\nLaw metrics look good! The event-based counting system is working correctly.")


if __name__ == "__main__":
    validate_law_metrics()
