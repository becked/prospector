#!/usr/bin/env python3
"""Test script to examine technology chart data."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tournament_visualizer.data.queries import TournamentQueries
from tournament_visualizer.data.database import get_database
from tournament_visualizer.components.charts import create_technology_comparison_chart
import json

# Get database
db = get_database()
queries = TournamentQueries(db)

# Get technology data for match 5 (Jams vs Nizar)
df = queries.get_technology_comparison(5)

print("DataFrame shape:", df.shape)
print("\nDataFrame columns:", df.columns.tolist())
print("\nDataFrame head:")
print(df.head(30))

print("\n\nGrouped by player:")
for player_name in df['player_name'].unique():
    player_df = df[df['player_name'] == player_name]
    print(f"\n{player_name}: {len(player_df)} technologies")
    print(player_df['tech_name'].tolist())

# Create the chart
fig = create_technology_comparison_chart(df)

# Inspect the chart data
print("\n\n=== CHART DATA ===")
print(f"Number of traces: {len(fig.data)}")
for i, trace in enumerate(fig.data):
    print(f"\nTrace {i}:")
    print(f"  Type: {trace.type}")
    print(f"  x values: {trace.x}")
    print(f"  y values: {trace.y}")
    if hasattr(trace, 'hovertext'):
        print(f"  hovertext length: {len(trace.hovertext) if trace.hovertext else 0}")
        if trace.hovertext:
            for j, ht in enumerate(trace.hovertext):
                print(f"  hovertext[{j}] preview: {ht[:200] if len(ht) > 200 else ht}")
