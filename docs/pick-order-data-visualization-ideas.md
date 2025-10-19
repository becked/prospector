# Pick Order Data Visualization Ideas

## Overview

Now that we're consuming first/second pick order information from the Google Sheets integration, we have rich data to analyze draft phase dynamics. This document outlines key questions to answer and visualization strategies for pick order data.

**Context**: In tournament games, one player picks their nation first, then the other picks second. Save files don't capture this, so we integrate it from the tournament organizer's spreadsheet.

---

## Key Questions to Answer

### 1. Does Pick Order Matter?

**The fundamental question**: Is there a first-pick or second-pick advantage?

**Metrics:**
- Overall win rate: first picker vs second picker
- Win rate by round (does it change in later rounds?)
- Win rate by game length (does advantage fade over time?)
- Win rate by skill level (do better players exploit pick order better?)

**Visualization Ideas:**

- **Simple stat card**: "First Pick Win Rate: 52.3%" with confidence interval
  - Show as prominent metric at top of dashboard
  - Include sample size and statistical significance indicator

- **Bar chart**: Win rate by pick position (first vs second)
  - Side-by-side bars
  - Error bars for confidence intervals
  - Annotation if difference is statistically significant

- **Line chart over rounds**: Does the advantage change as tournament progresses?
  - X-axis: Round number
  - Y-axis: Win rate
  - Two lines: first picker, second picker
  - Shows if meta evolves or players adapt

---

### 2. Nation Performance by Pick Position

Some nations might be stronger when picked first (aggressive early game) vs second (flexible counter-picks).

**Metrics:**
- Win rate for each nation when picked first vs second
- Delta between the two positions (which nations benefit most from each position)
- Sample size per nation/position combination

**Visualization Ideas:**

- **Grouped bar chart**: Each nation, two bars (first pick win rate, second pick win rate)
  - Nations sorted by total pick frequency
  - Color-coded bars (blue=first pick, red=second pick)
  - Helps identify position-dependent nations quickly

- **Scatter plot**: X=first pick WR, Y=second pick WR, diagonal line = equal performance
  - Each point is a nation (labeled)
  - Nations above diagonal prefer second pick
  - Nations below diagonal prefer first pick
  - Point size = total games played with that nation
  - Reveals position specialists at a glance

- **Heatmap**: Nations × Pick Position, colored by win rate
  - Rows: Nations
  - Columns: First Pick, Second Pick
  - Color gradient: Red (high WR) to Blue (low WR)
  - Easy visual scanning for best picks

- **Delta table**: Nations ranked by "position advantage"
  - Columns: Nation, First Pick WR, Second Pick WR, Delta
  - Sort by Delta to find biggest position effects
  - Highlights which nations care most about pick order

---

### 3. Counter-Pick Analysis

**This is the juicy stuff!** What nations beat what? Can second-pickers exploit first-picker choices?

**Metrics:**
- Head-to-head matchup matrix: Nation A (first pick) vs Nation B (second pick)
- "Counter effectiveness": How much better does Nation B perform when picked second against Nation A?
- Win rate compared to baseline (nation B's overall second-pick WR)
- Statistical significance of counter-pick advantage

**Visualization Ideas:**

- **Heatmap matrix**: Rows=first pick nations, Cols=second pick nations, color=second picker win rate
  - Red cells = good counter-picks (second picker wins often)
  - Blue cells = bad counter-picks (first picker dominates)
  - Hover tooltip: "Assyria vs Egypt: 12 games, 8-4 for Egypt (67%)"
  - Click cell → drill down to actual game list
  - Most actionable visualization for players

- **Network diagram**: Arrows from nation A → nation B if B is a strong counter
  - Node size = overall popularity
  - Edge thickness = strength of counter relationship
  - Only show statistically significant counters
  - Visual meta-game map

- **Top counters list**: "Best nations to pick second against Assyria: [Egypt 70%, Rome 65%]"
  - Searchable/filterable by first-pick nation
  - Shows top 5 counters with win rates
  - Include sample sizes for confidence
  - Practical reference guide for drafting

- **Matchup explorer (interactive)**:
  - Dropdown: Select nation picked first
  - Shows: Bar chart of all second-pick nations ranked by win rate
  - Highlights counters that exceed baseline WR
  - Sample size badges for reliability

---

### 4. Player Preferences & Strategies

Do players have pick order preferences? Do some players perform better in one position?

**Metrics:**
- Player win rate when picking first vs second
- Player's most-picked nations by position
- "Specialists": Players who consistently perform better in one position
- Pick order frequency (does player prefer first or second?)
- Consistency: variance in pick choices by position

**Visualization Ideas:**

- **Player profile card**: "Becked picks first 60% of the time, wins 55% as first picker, 48% as second picker"
  - Integration into existing player detail pages
  - Show favorite nations by position
  - Highlight if player has significant position preference

- **Table**: Players ranked by "pick order delta" (biggest advantage in one position)
  - Columns: Player, First Pick WR, Second Pick WR, Delta, Games
  - Sort to find position specialists
  - Filter by minimum games played
  - Reveals strategic archetypes

- **Scatter plot**: X=first pick WR, Y=second pick WR, label=player name
  - Diagonal line = balanced performance
  - Quadrant analysis: strong in both, weak in both, specialist
  - Point size = total games
  - Identifies player strengths/weaknesses

- **Player comparison view**:
  - Select two players
  - Side-by-side comparison of pick stats
  - Nation preferences by position
  - Head-to-head when they played each other (who picked what?)

---

### 5. Pick Order Trends Over Time

Does the meta evolve? Do certain nations become popular as counters?

**Metrics:**
- Most-picked nations by position over time (by round)
- Win rate trends for popular nations
- Counter-pick diversity (are people using varied counters or converging on a few?)
- Emergence of new strategies or meta shifts

**Visualization Ideas:**

- **Line chart**: Nation pick frequency by round (separate lines for first/second pick)
  - X-axis: Round number
  - Y-axis: Pick rate (%)
  - Multiple lines for top 5-7 nations
  - Shows meta evolution

- **Stacked area chart**: Distribution of nations picked in each position over rounds
  - X-axis: Round number
  - Y-axis: 100% stacked pick distribution
  - Each area = one nation
  - Shows market share shifts over tournament

- **Timeline annotations**: "Round 3: Egypt emerges as dominant counter to Assyria"
  - Timeline of notable meta shifts
  - Auto-detected or manually annotated
  - Links to relevant games/matches

- **Win rate evolution**:
  - Line chart showing nation win rates over time
  - Split by pick position
  - Identifies if nations get figured out or discovered

---

## Dashboard Organization

Suggested layout for integrating pick order data into the existing dashboard:

### **Overview Section**

**Purpose**: High-level pick order impact summary

**Components**:
- Overall first/second pick win rate (big stat card)
  - "First Pick Win Rate: 52.3% (48-40 record)"
  - Confidence interval and p-value
  - Color-coded: green if significant, gray if not

- Pick distribution pie chart
  - How many games had each position win
  - Simple visual balance check

- Coverage metric: "Pick order data available for 85% of matches"
  - Data quality indicator
  - Link to unmatched games list

- Quick stats:
  - Most common first-pick nation
  - Most common second-pick nation
  - Highest counter-pick win rate

### **Nation Analysis Section**

**Purpose**: Deep dive into nation-specific pick order dynamics

**Components**:
- Nation performance by pick position (grouped bar chart or scatter)
  - Shows which nations care about pick order
  - Sortable/filterable

- Counter-pick heatmap (interactive, hover for details)
  - **PRIORITY FEATURE** - most actionable for players
  - Full matchup matrix
  - Click-through to game details

- Top nations picked first vs second (two lists side-by-side)
  - Pick frequency rankings
  - Shows draft meta preferences

- Nation detail pages (expand existing):
  - Add pick order tabs/sections
  - "Performance as First Pick" vs "Performance as Second Pick"
  - "Best matchups when picked first/second"
  - "Common counter-picks against this nation"

### **Player Insights Section**

**Purpose**: Individual player pick strategies and performance

**Components**:
- Player pick order performance table (sortable)
  - All players, sortable by any column
  - Columns: Name, Games, First Pick %, First Pick WR, Second Pick WR, Delta
  - Highlights position specialists

- Individual player cards with pick stats
  - Integrate into existing player profiles
  - Show pick preferences and performance

- Player comparison tool
  - Compare two players' pick strategies
  - Side-by-side stats

- Integration into existing player detail pages
  - New "Pick Order" tab
  - Favorite nations by position
  - Performance breakdown by position

### **Matchup Analysis Section**

**Purpose**: Tactical counter-pick reference and analysis

**Components**:
- Interactive matchup explorer: "Select nation picked first → see best counters"
  - Dropdown for first-pick selection
  - Dynamic bar chart of counter performance
  - Sample size indicators

- Historical matchup results table
  - Filterable by nation, player, round
  - Shows actual game outcomes
  - Links to game details

- "Most decisive counter-picks" (biggest win rate swings)
  - Ranked list of strongest counter relationships
  - Min sample size filter
  - Statistical significance badges

- Matchup detail view
  - Select specific matchup (Nation A vs Nation B)
  - Shows all games with that pairing
  - Win rate, average game length, common outcomes
  - Player performance in this specific matchup

---

## Technical Considerations

### Data Quality Indicators

Since not all matches will have pick order data:

- **Always show coverage %**: "Based on 42 of 50 matches (84% coverage)"
- **Filter or note when sample size is too small**:
  - Gray out or hide cells with <5 games
  - Show warning icon: "⚠️ Small sample size (3 games)"
  - Configurable minimum threshold

- **Handle NULL values gracefully**:
  - Unmatched games don't break charts
  - Clear messaging: "Pick order data not available for this match"
  - Option to filter out unmatched games

- **Data quality page**:
  - List unmatched games
  - Show matching confidence scores
  - Link to override configuration

### Statistical Significance

With limited sample sizes, avoid misleading conclusions:

- **Show confidence intervals** where appropriate
  - Especially for win rate comparisons
  - Use binomial confidence intervals
  - Wilson score interval recommended (better for small n)

- **Highlight results with small sample sizes**:
  - Badge system: "⚠️ n=3" for unreliable stats
  - Color coding: faded for low confidence
  - Tooltip warnings

- **Consider binomial confidence intervals** for win rates:
  - More accurate than normal approximation for small samples
  - Shows uncertainty visually

- **Statistical significance tests**:
  - Chi-square test for pick position advantage
  - Fisher's exact test for specific matchups
  - Show p-values where relevant
  - Don't hide non-significant results (still informative!)

### Interactivity

Make the data explorable:

- **Filters**:
  - Round number (early vs late tournament)
  - Date range (meta evolution)
  - Player skill tier (if available)
  - Minimum games threshold
  - Statistical significance only

- **Drill-down**:
  - Click nation in heatmap → see all games with that matchup
  - Click player → see their pick history
  - Click stat → see underlying data
  - Breadcrumb navigation for multi-level drill-down

- **Tooltips**:
  - Hover over heatmap cell → "Assyria vs Egypt: 12 games, 8-4 for Egypt (67%)"
  - Hover over bar → full stats with confidence interval
  - Hover over player → quick stats preview

- **Sorting and ranking**:
  - Tables sortable by any column
  - Multiple sort keys
  - Persistent sort preferences

- **Export/share**:
  - Download chart as image
  - Export underlying data as CSV
  - Shareable URLs for specific views

### Integration with Existing Features

Leverage existing dashboard infrastructure:

- **Add pick order columns to existing tables**:
  - Match history: show who picked first
  - Player stats: add pick order performance columns
  - Civilization stats: split by pick position

- **Show pick order in game detail pages**:
  - "Match 42: Becked picked Assyria first, Anarkos countered with Egypt"
  - Visual indicator of pick order
  - Link to counter-pick analysis for that matchup

- **Include in civilization performance breakdowns**:
  - Existing civ stats: add "As First Pick" and "As Second Pick" tabs
  - Compare civ performance across pick positions
  - Highlight position-dependent civs

- **Player profile enhancements**:
  - Add "Pick Strategy" section
  - Show favorite nations by position
  - Performance metrics split by pick order

- **Reuse existing chart components**:
  - Same styling and theming
  - Consistent interaction patterns
  - Shared filter controls

---

## Implementation Priority

If implementing incrementally, suggested order:

### Phase 1: Foundation (MVP)
**Goal**: Answer the basic question and provide most actionable insight

1. **Overview stats card**: First vs second pick win rate
   - Simple, quick to implement
   - Answers fundamental question
   - High visibility

2. **Counter-pick heatmap**: Interactive matchup matrix
   - Most unique and actionable visualization
   - Directly useful for players drafting
   - High engagement potential
   - Provides tactical value

**Why start here**: Provides immediate value with manageable scope. Heatmap is the "killer feature" that distinguishes this from generic stats.

### Phase 2: Nation Analysis
**Goal**: Deep dive into which nations benefit from pick order

3. **Nation performance by position**: Grouped bar chart or scatter plot
   - Shows which nations are position-dependent
   - Helps players choose nations strategically

4. **Top nations by position**: Side-by-side lists
   - Simple reference
   - Shows draft meta

5. **Nation detail pages**: Add pick order sections
   - Integrates into existing navigation
   - Contextual insights

### Phase 3: Player Insights
**Goal**: Individual player strategies and preferences

6. **Player pick order table**: Sortable performance breakdown
   - Identifies specialists
   - Competitive leaderboard aspect

7. **Player profile integration**: Add pick stats to existing pages
   - Natural fit with current UI
   - Per-player drill-down

8. **Player comparison tool**: Side-by-side pick analysis
   - Supports strategic planning
   - Head-to-head context

### Phase 4: Advanced Analysis
**Goal**: Meta trends and deep exploration

9. **Matchup explorer**: Interactive counter-pick tool
   - "What should I pick against X?"
   - Practical reference guide

10. **Trends over time**: Meta evolution charts
    - Shows how draft strategy evolves
    - Historical context

11. **Data quality dashboard**: Unmatched games, coverage stats
    - Transparency
    - Debugging aid

---

## Success Metrics

How to measure if these visualizations are effective:

**Engagement Metrics**:
- Time spent on pick order pages
- Click-through rates on interactive elements
- Filter usage frequency
- Return visits to counter-pick heatmap

**Utility Metrics**:
- Player feedback on usefulness
- Adoption in tournament preparation (anecdotal)
- Questions answered (reduced support inquiries)

**Data Quality Metrics**:
- Pick order coverage % (goal: >90%)
- Match accuracy rate (goal: >95%)
- Time to sync/update (goal: <5 minutes)

**Technical Metrics**:
- Page load time (goal: <2 seconds)
- Chart render time (goal: <500ms)
- Data freshness (goal: updated within 1 hour of new games)

---

## Open Questions

Things to investigate or decide:

1. **Sample size thresholds**: What's the minimum number of games before we trust a stat?
   - Counter-pick matchup: 5 games?
   - Overall pick position: 20 games?
   - Player position preference: 10 games?

2. **Statistical tests**: Which tests are most appropriate?
   - Binomial test for overall pick advantage?
   - Chi-square for independence?
   - Fisher's exact for small samples?

3. **UI placement**: Where do these features live?
   - New "Draft Analysis" top-level tab?
   - Integrated into existing tabs?
   - Separate dashboard page?

4. **Mobile support**: How do complex heatmaps work on small screens?
   - Simplified mobile views?
   - Scrollable/zoomable matrices?
   - Mobile-first alternative visualizations?

5. **Performance**: With full tournament data, will heatmaps render quickly?
   - Pre-compute aggregates?
   - Lazy load details?
   - Cache strategies?

6. **Color schemes**: Best palette for win rate heatmaps?
   - Red-blue diverging (intuitive but overused)?
   - Single-hue sequential (less dramatic)?
   - Colorblind-friendly options?

---

## Notes

- Pick order data depends on Google Sheets integration working reliably
- Not all matches will have pick order data (historical matches, data quality issues)
- Statistical rigor is critical given small sample sizes in many matchups
- Most valuable feature is likely the counter-pick heatmap - prioritize polish here
- Integration with existing features is more valuable than standalone pages
- Consider player skill levels in analysis (do good players exploit pick order better?)
- Watch for selection bias (do stronger players get first pick more often?)

---

## Related Documentation

- Implementation plan: `docs/plans/pick-order-integration-implementation-plan.md`
- Schema migration: `docs/migrations/008_add_pick_order_tracking.md`
- Analytics examples: `scripts/pick_order_analytics_examples.sql`
- Google Sheets integration: See CLAUDE.md "Pick Order Data Integration" section
