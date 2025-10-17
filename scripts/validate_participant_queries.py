"""Validate participant linking in cross-match queries."""

from tournament_visualizer.data.queries import get_queries


def main() -> None:
    queries = get_queries()

    print("=" * 60)
    print("Participant Linking Validation Report")
    print("=" * 60)

    # Test 1: Law progression by match
    print("\n1. Law Progression by Match (all matches)")
    df = queries.get_law_progression_by_match(match_id=None)
    total_rows = len(df)
    linked = (~df['is_unlinked']).sum()
    unlinked = df['is_unlinked'].sum()
    print(f"   Total match-player instances: {total_rows}")
    print(f"   Linked to participants: {linked} ({linked/total_rows*100:.1f}%)")
    print(f"   Unlinked: {unlinked} ({unlinked/total_rows*100:.1f}%)")

    # Test 2: Map performance analysis
    print("\n2. Map Performance Analysis")
    df = queries.get_map_performance_analysis()
    print(f"   Total map configurations: {len(df)}")
    print(f"   Total unique participants: {df['unique_participants'].sum()}")
    print(f"   Linked: {df['unique_linked_participants'].sum()}")
    print(f"   Unlinked: {df['unique_unlinked_players'].sum()}")

    # Verify sum property
    sum_check = (
        df['unique_linked_participants'] + df['unique_unlinked_players']
        == df['unique_participants']
    ).all()
    print(f"   Sum check (linked + unlinked = total): {'✓ PASS' if sum_check else '✗ FAIL'}")

    # Test 3: Player law progression stats
    print("\n3. Player Law Progression Stats")
    df = queries.get_player_law_progression_stats()
    total_players = len(df)
    linked = (~df['is_unlinked']).sum()
    unlinked = df['is_unlinked'].sum()
    print(f"   Total unique players: {total_players}")
    print(f"   Linked to participants: {linked} ({linked/total_players*100:.1f}%)")
    print(f"   Unlinked: {unlinked} ({unlinked/total_players*100:.1f}%)")

    print("\n" + "=" * 60)
    print("Validation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
