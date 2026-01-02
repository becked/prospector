"""Debug script for pick order charts."""

from tournament_visualizer.data.queries import get_queries

# Test the query with no filters (simulating default dashboard state)
queries = get_queries()

print("Testing get_pick_order_win_rates with no filters...")
df = queries.get_pick_order_win_rates()

if df.empty:
    print("❌ Result is EMPTY")

    # Check if _get_filtered_match_ids returns anything
    match_ids = queries._get_filtered_match_ids()
    print(f"Match IDs from filter: {match_ids}")
    print(f"Number of match IDs: {len(match_ids)}")
else:
    print("✅ Result has data:")
    print(df)

# Also test with filters similar to default dashboard state
print("\n\nTesting with turn_length filter (max_turns=200)...")
df2 = queries.get_pick_order_win_rates(max_turns=200)

if df2.empty:
    print("❌ Result is EMPTY")

    # Check if _get_filtered_match_ids returns anything
    match_ids2 = queries._get_filtered_match_ids(max_turns=200)
    print(f"Match IDs from filter: {match_ids2}")
    print(f"Number of match IDs: {len(match_ids2)}")
else:
    print("✅ Result has data:")
    print(df2)
