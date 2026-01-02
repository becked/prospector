# Feature: Win Rate vs Science Production Correlation Analysis

> **Status:** Planned
> **Target Location:** Overview Page → Summary Tab (above matches table)
> **Purpose:** Visualize the relationship between science production and game outcomes to identify strategic correlations

## Overview

This feature adds three scatter plot visualizations showing the correlation between science production metrics and win rates on a per-game basis. Each point represents a single game, with statistical overlays to identify trends.

**Primary Question:** Does higher science production in a game correlate with winning that game?

**Secondary Insight:** Which science metric (efficiency, peak output, or total production) has the strongest correlation with wins?

## Data Sources

### Required Tables
- `player_yield_history` - Turn-by-turn yield production rates
- `match_winners` - Game outcomes (who won each match)
- `players` - Player metadata (names, participant linkage)
- `matches` - Match metadata

### Data Structure

Each game has 2+ players. For each player in each game, we calculate:

1. **Average Science Per Turn**
   ```sql
   AVG(amount / 10.0) WHERE resource_type = 'YIELD_SCIENCE'
   GROUP BY match_id, player_id
   ```

2. **Final-Turn Science Rate**
   ```sql
   MAX(amount / 10.0) WHERE resource_type = 'YIELD_SCIENCE'
   GROUP BY match_id, player_id
   ```

3. **Total Science Production**
   ```sql
   SUM(amount / 10.0) WHERE resource_type = 'YIELD_SCIENCE'
   GROUP BY match_id, player_id
   ```

4. **Win/Loss Status**
   ```sql
   CASE WHEN mw.winner_player_id = p.player_id THEN 1 ELSE 0 END
   ```

**Critical Note:** Science values in `player_yield_history.amount` are stored as raw integers and must be divided by 10 for display (see `docs/archive/reports/yield-display-scale-issue.md`).

## Implementation Plan

### 1. Query Layer (`tournament_visualizer/data/queries.py`)

Add new method to `TournamentQueries` class:

```python
def get_science_win_correlation(self) -> pd.DataFrame:
    """Get per-game science metrics and win/loss outcomes.

    Returns one row per player per game with:
    - match_id, player_id, player_name
    - avg_science_per_turn: Average YIELD_SCIENCE across all turns (display-ready)
    - final_turn_science: Science production rate on final turn (display-ready)
    - total_science: Sum of all science production (display-ready)
    - won: 1 if player won, 0 if lost
    - total_turns: Game length for context

    Returns:
        DataFrame with science metrics and win/loss data per game
    """
```

**Query Structure:**

```sql
WITH science_metrics AS (
    SELECT
        yh.match_id,
        yh.player_id,
        AVG(yh.amount / 10.0) as avg_science_per_turn,
        MAX(yh.amount / 10.0) as final_turn_science,
        SUM(yh.amount / 10.0) as total_science,
        COUNT(*) as turns_with_science
    FROM player_yield_history yh
    WHERE yh.resource_type = 'YIELD_SCIENCE'
    GROUP BY yh.match_id, yh.player_id
)
SELECT
    sm.match_id,
    sm.player_id,
    p.player_name,
    sm.avg_science_per_turn,
    sm.final_turn_science,
    sm.total_science,
    CASE WHEN mw.winner_player_id = sm.player_id THEN 1 ELSE 0 END as won,
    m.total_turns
FROM science_metrics sm
JOIN players p ON sm.match_id = p.match_id AND sm.player_id = p.player_id
JOIN matches m ON sm.match_id = m.match_id
LEFT JOIN match_winners mw ON sm.match_id = mw.match_id
ORDER BY sm.match_id, sm.player_id
```

**Edge Cases:**
- Handle games with no match_winners entry (treat as loss for all players)
- Filter out games with 0 science turns (shouldn't happen, but defensive)

### 2. Chart Layer (`tournament_visualizer/charts.py`)

Add three new chart creation functions:

#### Chart 1: Average Science Per Turn vs Win Rate

```python
def create_science_per_turn_correlation_chart(df: pd.DataFrame) -> go.Figure:
    """Create scatter plot: average science/turn vs win/loss.

    Args:
        df: DataFrame from get_science_win_correlation()

    Returns:
        Plotly figure with:
        - X-axis: avg_science_per_turn
        - Y-axis: won (0 or 1, jittered for visibility)
        - Point colors: Wins (green) vs Losses (red)
        - Trend line: Logistic regression fit
        - R² annotation
    """
```

**Visual Specifications:**
- **Base**: Use `create_base_figure()` for consistency
- **Scatter points**:
  - X: `avg_science_per_turn`
  - Y: `won` with random jitter (±0.05) for visibility at 0 and 1
  - Colors: Winners (green), Losers (red)
  - Size: 8px
  - Opacity: 0.6 (to show overlap)
  - Hover: `player_name`, exact science value, match_id
- **Trend line**:
  - Logistic regression curve (since Y is binary)
  - Or simple linear regression for simplicity
  - Dashed line, gray color
- **Annotations**:
  - R² value in top-right corner
  - Median science line (vertical, dotted)
- **Axes**:
  - X-axis: "Average Science Per Turn"
  - Y-axis: "Game Outcome" with custom tick labels ["Loss", "Win"]
- **Height**: 400px (standard)

#### Chart 2: Final-Turn Science vs Win Rate

```python
def create_final_science_correlation_chart(df: pd.DataFrame) -> go.Figure:
    """Create scatter plot: final-turn science vs win/loss.

    Same structure as Chart 1, but using final_turn_science on X-axis.
    """
```

**Differences from Chart 1:**
- X-axis: "Final Turn Science Rate"
- Same Y-axis, colors, and statistical overlays

#### Chart 3: Total Science vs Win Rate

```python
def create_total_science_correlation_chart(df: pd.DataFrame) -> go.Figure:
    """Create scatter plot: total science production vs win/loss.

    Same structure as Chart 1, but using total_science on X-axis.
    May want to normalize by game length (total_turns).
    """
```

**Differences from Chart 1:**
- X-axis: "Total Science Production"
- Consider: "Science Per Turn Played" (total_science / total_turns) instead of raw total
  - Decision: Use normalized version to account for game length variance
  - X-axis label: "Science Per Turn Played (Total ÷ Game Length)"

**Implementation Notes:**
- All three charts follow identical pattern (DRY opportunity)
- Consider helper function: `_create_correlation_scatter(df, x_col, x_label)`
- Use consistent color scheme across all three
- Empty state: If `df.empty`, return `create_empty_figure("No science data available")`

### 3. UI Integration (`tournament_visualizer/pages/page_overview.py`)

**Location:** Summary tab, above the matches table

**Layout Structure:**

```python
# In create_summary_tab() function, add BEFORE matches table:

dbc.Row([
    dbc.Col([
        create_chart_card(
            title="Average Science Per Turn vs Win Rate",
            chart_id="overview-science-per-turn-correlation",
            body_id="overview-science-per-turn-correlation-body"
        )
    ], width=4),
    dbc.Col([
        create_chart_card(
            title="Final-Turn Science vs Win Rate",
            chart_id="overview-final-science-correlation",
            body_id="overview-final-science-correlation-body"
        )
    ], width=4),
    dbc.Col([
        create_chart_card(
            title="Total Science vs Win Rate",
            chart_id="overview-total-science-correlation",
            body_id="overview-total-science-correlation-body"
        )
    ], width=4),
], className="mb-4"),

# Then existing matches table below...
```

**Callback:**

```python
@callback(
    Output("overview-science-per-turn-correlation", "figure"),
    Output("overview-final-science-correlation", "figure"),
    Output("overview-total-science-correlation", "figure"),
    Input("url", "pathname"),  # Trigger on page load
)
def update_science_correlation_charts(pathname: str) -> Tuple[go.Figure, go.Figure, go.Figure]:
    """Update all three science correlation charts.

    Returns:
        Tuple of (science_per_turn_fig, final_science_fig, total_science_fig)
    """
    try:
        queries = get_queries()
        df = queries.get_science_win_correlation()

        if df.empty:
            empty_fig = create_empty_figure("No science data available")
            return empty_fig, empty_fig, empty_fig

        fig1 = create_science_per_turn_correlation_chart(df)
        fig2 = create_final_science_correlation_chart(df)
        fig3 = create_total_science_correlation_chart(df)

        return fig1, fig2, fig3

    except Exception as e:
        logger.error(f"Error creating science correlation charts: {e}")
        error_fig = create_empty_figure("Error loading correlation data")
        return error_fig, error_fig, error_fig
```

**Component IDs:**
- `overview-science-per-turn-correlation` (Chart 1 figure)
- `overview-science-per-turn-correlation-body` (Card body wrapper)
- `overview-final-science-correlation` (Chart 2 figure)
- `overview-final-science-correlation-body` (Card body wrapper)
- `overview-total-science-correlation` (Chart 3 figure)
- `overview-total-science-correlation-body` (Card body wrapper)

**Styling:**
- 3-column grid (width=4 each, Bootstrap 12-column system)
- Margin bottom: `mb-4` for spacing before matches table
- Use `create_chart_card()` helper for consistent card styling

### 4. Statistical Overlays

**Trend Line Implementation:**

For binary outcomes (win/loss), use logistic regression or simple linear approximation:

```python
from scipy.stats import linregress
import numpy as np

# Linear approximation (simpler)
x = df['avg_science_per_turn'].values
y = df['won'].values
slope, intercept, r_value, p_value, std_err = linregress(x, y)

# Generate trend line points
x_trend = np.linspace(x.min(), x.max(), 100)
y_trend = slope * x_trend + intercept

# Add to figure
fig.add_trace(go.Scatter(
    x=x_trend,
    y=y_trend,
    mode='lines',
    name='Trend',
    line=dict(color='gray', dash='dash'),
    showlegend=True
))

# Add R² annotation
r_squared = r_value ** 2
fig.add_annotation(
    x=0.95, y=0.95,
    xref='paper', yref='paper',
    text=f'R² = {r_squared:.3f}',
    showarrow=False,
    bgcolor='white',
    bordercolor='gray',
    borderwidth=1
)
```

**Median Line:**

```python
median_science = df['avg_science_per_turn'].median()

fig.add_vline(
    x=median_science,
    line_dash="dot",
    line_color="gray",
    annotation_text=f"Median: {median_science:.1f}",
    annotation_position="top"
)
```

**Quartile Markers (optional):**

```python
q1 = df['avg_science_per_turn'].quantile(0.25)
q3 = df['avg_science_per_turn'].quantile(0.75)

fig.add_vrect(
    x0=q1, x1=q3,
    fillcolor="gray",
    opacity=0.1,
    layer="below",
    line_width=0,
    annotation_text="IQR",
    annotation_position="top left"
)
```

## Technical Considerations

### 1. Y-Axis Jitter

Since `won` is binary (0 or 1), points will overlap. Add random jitter:

```python
import numpy as np

df['won_jittered'] = df['won'] + np.random.uniform(-0.05, 0.05, size=len(df))
```

Use `won_jittered` for plotting, but show actual `won` in hover data.

### 2. Data Volume

With 34 matches and average 2 players per match:
- ~68 data points per chart
- Low enough for instant rendering
- Statistical significance may be limited (note in chart or docs)

### 3. Missing Data Handling

**Scenario:** Match has no winner recorded in `match_winners`

**Solution:** LEFT JOIN ensures all players are included, `won` defaults to 0

**Alternative:** Filter out matches with no winner (cleaner but loses data)

```sql
-- Option 1: Include all (current approach)
LEFT JOIN match_winners mw ON sm.match_id = mw.match_id

-- Option 2: Exclude matches without winners
INNER JOIN match_winners mw ON sm.match_id = mw.match_id
WHERE mw.winner_player_id IS NOT NULL
```

**Recommendation:** Use Option 1 (LEFT JOIN) to maximize data usage.

### 4. Performance

**Current Scale:** Negligible (68 rows, simple aggregations)

**Future Scale:** If dataset grows to 1000+ matches:
- Add index: `CREATE INDEX idx_yield_history_science ON player_yield_history(match_id, player_id) WHERE resource_type = 'YIELD_SCIENCE'`
- Consider caching query results (unlikely to be needed)

### 5. Color Accessibility

Use colorblind-friendly palette:
- Wins: `#2ca02c` (green)
- Losses: `#d62728` (red)
- Trend line: `#7f7f7f` (gray)

## Testing Checklist

- [ ] Query returns expected columns and data types
- [ ] Query handles matches with no winners gracefully
- [ ] Query correctly divides science values by 10
- [ ] Charts render with empty DataFrame (show empty state)
- [ ] Charts render with single data point
- [ ] Charts render with full dataset
- [ ] Trend line calculates correctly
- [ ] R² displays with proper formatting
- [ ] Hover tooltips show correct player names and values
- [ ] Y-axis jitter makes overlapping points visible
- [ ] All three charts display side-by-side in 3-column grid
- [ ] Charts appear above matches table on Summary tab
- [ ] No console errors on page load
- [ ] Responsive layout works on smaller screens

## Future Enhancements

1. **Interactive Filtering:**
   - Click a point to filter matches table below
   - Filter by civilization or map type

2. **Additional Metrics:**
   - Other yield types (CIVICS, TRAINING, CULTURE)
   - Multi-metric correlation matrix

3. **Statistical Tests:**
   - P-value significance testing
   - Confidence intervals on trend line

4. **Comparative Analysis:**
   - Winner vs loser science in same game (paired comparison)
   - Science differential as predictor

5. **Temporal Analysis:**
   - Science trajectory over time (early, mid, late game phases)
   - Turn-by-turn science growth rate

## References

- **Yield Display Scale:** `docs/archive/reports/yield-display-scale-issue.md`
- **Query Patterns:** `tournament_visualizer/data/queries.py`
- **Chart Conventions:** `docs/ui-architecture.md`
- **Database Schema:** `docs/database-schema.md`
