# Tournament Visualizer UI Issues Report

**Date:** October 7, 2025  
**Tester:** Automated Browser Testing via Playwright MCP  
**Application:** Old World Tournament Visualizer

## Executive Summary

This report documents UI/UX issues discovered during systematic testing of all pages in the Tournament Visualizer application. The testing revealed several critical issues with non-functional panels, missing data, and incomplete features.

---

## Overview Page

**URL:** http://127.0.0.1:8050/  
**Screenshot:** `screenshots/overview-page.png`

### ✅ Working Features
- Page loads successfully
- Summary statistics display correctly (15 matches, 25 players, 809 turns avg, 0 events)
- Match Timeline graph renders with data
- Recent Match Lengths graph displays correctly
- Top Player Performance chart shows data (all at 100% win rate)
- Civilization Performance chart renders properly
- Match Duration Distribution histogram shows
- Victory Conditions analysis displays
- Recent Matches table populates with all 15 matches
- Date range filter (Last 90 days) is functional
- Refresh button present

### ⚠️ Issues Identified
1. **Date Display Error**: Match Timeline x-axis shows "Sep 82025" instead of "Sep 8, 2025"
2. **Score Data Missing**: Civilization table shows "Avg Score: 0.0" for all entries
3. **Player Win Rate Anomaly**: All top 10 players show exactly 100% win rate - likely a data filtering or calculation issue
4. **Events Count**: Shows "0 Total Events" - unclear if this is correct or if event tracking is broken

---

## Matches Page

**URL:** http://127.0.0.1:8050/matches  
**Screenshots:** 
- `screenshots/matches-page-empty.png`
- `screenshots/matches-page-no-results.png`

### ❌ Critical Issue: Non-Functional Match Selector

**Problem:** The match dropdown shows "No results found" despite 15 matches being available in the database.

**Details:**
- Dropdown placeholder: "Choose a match to analyze..."
- When clicked, displays: "No results found"
- Page shows empty state: "Select a Match - Choose a match from the dropdown above to view detailed analysis"
- Breadcrumb navigation works (Home / Matches)
- Refresh button present but ineffective

**Impact:** The entire Matches page is **completely non-functional** - users cannot view any match details.

**Root Cause:** The match dropdown is not being populated with data from the database. This suggests:
- Query failure in the callback
- Data transformation issue
- Dropdown options not being formatted correctly

---

## Players Page

**URL:** http://127.0.0.1:8050/players  
**Screenshots:**
- `screenshots/players-page-no-data.png`
- `screenshots/players-civ-analysis.png`
- `screenshots/players-head-to-head.png`
- `screenshots/players-performance-trends.png`

### Tab 1: Player Rankings

**Screenshot:** `screenshots/players-page-no-data.png`

#### ❌ Critical Issue: No Player Data Displayed

**Problems:**
1. Summary cards all show no/invalid data:
   - Active Players: 0 (should be 25)
   - Average Win Rate: N/A
   - Most Active: N/A
   - Top Performer: N/A

2. Charts show "No players match the selected criteria":
   - Top Players by Win Rate (empty)
   - Player Activity (Total Matches) (empty)

3. Player Performance Rankings table is completely empty (no data rows)

**Filters Present:**
- Date Range: "All time" (selected)
- Civilizations: Multi-select dropdown
- Minimum Matches: Slider (default value 3)

**Impact:** The Player Rankings tab is **completely non-functional** despite having player data in the system.

**Root Cause:** The minimum matches filter (default value: 3) appears to be filtering out all players. With only 15 total matches and likely only 1-2 matches per player, no players meet the threshold.

### Tab 2: Civilization Analysis

**Screenshot:** `screenshots/players-civ-analysis.png`

#### ✅ Partially Working

**Working Features:**
- Civilization Win Rates chart displays correctly
- Civilization Popularity pie chart shows data
- Civilization Statistics table populates with 9 civilizations

**Data Displayed:**
- Egypt: 2 matches, 2 wins, 100% win rate
- Hittite: 2 matches, 2 wins, 100% win rate
- Carthage: 2 matches, 2 wins, 100% win rate
- Assyria: 4 matches, 3 wins, 75% win rate
- Kush: 2 matches, 1 win, 50% win rate
- Greece: 5 matches, 2 wins, 40% win rate
- Aksum: 3 matches, 1 win, 33.3% win rate
- Rome: 3 matches, 1 win, 33.3% win rate
- Persia: 5 matches, 1 win, 20% win rate

#### ⚠️ Issues:
1. **Score Data Missing**: All civilizations show "Avg Score: 0.0"
2. **Tab Inherits Broken Filter**: Same minimum matches filter (value: 3) is applied but doesn't break this view since it filters by civilization, not player

### Tab 3: Head-to-Head

**Screenshot:** `screenshots/players-head-to-head.png`

#### ❌ Critical Issue: Non-Functional Player Selectors

**Problems:**
1. Player 1 dropdown: "Select first player..." - no options available
2. Player 2 dropdown: "Select second player..." - no options available
3. Empty state message: "Select Two Players - Choose two players from the dropdowns above to compare their head-to-head record"

**Impact:** Head-to-Head comparison is **completely non-functional** - users cannot select any players.

**Root Cause:** Similar to the Matches page, player dropdowns are not being populated. This is likely due to the same minimum matches filter blocking all players.

### Tab 4: Performance Trends

**Screenshot:** `screenshots/players-performance-trends.png`

#### ⚠️ Issues: Empty Visualizations

**Problems:**
1. **Player vs Civilization Matrix**: Shows only axis labels (−1 to 6 on both axes), no actual data/heatmap
2. **Performance Over Time**: Shows only axis labels (−1 to 6 on both axes), no trend lines or data points

**Impact:** Performance trends analysis is **non-functional** - no meaningful data visualization.

**Root Cause:** Likely related to the same filter issue preventing player data from being loaded.

---

## Maps Page

**URL:** http://127.0.0.1:8050/maps  
**Screenshots:**
- `screenshots/maps-page-performance.png`
- `screenshots/maps-territory-analysis.png`
- `screenshots/maps-strategic-analysis.png`

### Tab 1: Map Performance

**Screenshot:** `screenshots/maps-page-performance.png`

#### ✅ Fully Functional

**Working Features:**
- Summary cards display correct data:
  - 4 Map Types
  - 749 turns avg game length
  - "Smallest" most popular size
  - "Smallest" longest games (1031 turns avg)
- Game Length by Map Size chart renders correctly
- Map Popularity pie chart shows 93.3% Smallest, 6.67% Tiny
- Map Statistics table populates with 4 rows of data

**Data Quality:** All data appears accurate and consistent.

### Tab 2: Territory Analysis

**Screenshot:** `screenshots/maps-territory-analysis.png`

#### ❌ Critical Issue: Match Selector Not Working

**Problems:**
1. Match dropdown shows: "Choose a match to analyze territories..."
2. Turn Range slider present (0-100) but inactive
3. All three visualizations show placeholder messages:
   - Territory Control Over Time: "Select a match to view territory control"
   - Final Territory Distribution: "Select a match"
   - Territory Control Heatmap: "Select a match to view territory heatmap"

**Impact:** Territory analysis is **completely non-functional** - users cannot select any match to analyze.

**Root Cause:** Same issue as Matches page - dropdown not being populated with match data.

### Tab 3: Strategic Analysis

**Screenshot:** `screenshots/maps-strategic-analysis.png`

#### ⚠️ Partially Implemented

**Working Features:**
- Map Class Performance chart displays data correctly (Coastalrainbasin: 1031, Mapscriptcontinent: 668, Mapscriptinlandsea2: 629)

**Not Implemented:**
1. **Starting Position Impact**: Shows "Starting position analysis not yet implemented"
2. **Territory Expansion Patterns**: Shows "Expansion pattern analysis not yet implemented"

**Status:** This tab is **partially complete** with placeholder messages indicating future development.

---

## Common Issues Across All Pages

### 1. Filter Default Value Problem

**Severity:** CRITICAL

The "Minimum Matches" filter on the Players page defaults to 3, which filters out all players in a dataset with only 15 total matches. This cascading filter breaks:
- Player Rankings tab (all cards show N/A, empty charts/table)
- Head-to-Head tab (no players available for selection)
- Performance Trends tab (no data to visualize)

**Recommendation:** Change default value to 1 or make filter more intelligent based on actual match distribution.

### 2. Dropdown Population Failures

**Severity:** CRITICAL

Multiple dropdown selectors fail to populate with data:
- Matches page: match selector
- Players page: player selectors in Head-to-Head
- Maps/Territory Analysis: match selector

**Pattern:** All affected dropdowns show placeholder text but display "No results found" or remain empty when clicked.

**Recommendation:** Debug the callback functions that populate these dropdowns. Check for:
- Database query failures
- Data format mismatches
- Filter conflicts
- Async loading issues

### 3. Missing Score Data

**Severity:** MEDIUM

Throughout the application, "Avg Score" consistently shows 0.0:
- Overview page: Civilization Performance table
- Players page: Civilization Statistics table

**Recommendation:** Investigate whether:
- Score data is not being captured during import
- Score field exists but is not being read
- Score calculation logic is broken

### 4. Incomplete Features

**Severity:** LOW

Maps/Strategic Analysis tab explicitly shows placeholder messages for unimplemented features:
- Starting Position Impact
- Territory Expansion Patterns

**Recommendation:** Either complete these features or remove the placeholder panels to avoid confusion.

---

## Priority Recommendations

### P0 - Critical (Breaks Core Functionality)

1. **Fix Matches Page Dropdown** - Users cannot view any match details
2. **Fix Players Page Default Filter** - Prevents all player data from displaying
3. **Fix Head-to-Head Player Selectors** - Feature is completely broken
4. **Fix Territory Analysis Match Selector** - Feature is completely broken

### P1 - High (Degrades User Experience)

5. **Debug Score Data Pipeline** - Score values are always 0.0
6. **Fix Performance Trends Visualizations** - Empty matrix and timeline charts
7. **Investigate Player Win Rate Data** - All top players showing 100% seems incorrect

### P2 - Medium (Polish & Completeness)

8. **Fix Date Format** - "Sep 82025" should be "Sep 8, 2025"
9. **Complete Strategic Analysis Features** - Remove placeholders or implement features
10. **Validate Events Counter** - Confirm if "0 Total Events" is correct

---

## Testing Methodology

- **Tool:** Playwright MCP for browser automation
- **Approach:** Systematic navigation through all pages and tabs
- **Coverage:** 100% of accessible UI elements
- **Screenshots:** Captured for all major views
- **Date:** October 7, 2025

---

## Conclusion

The Tournament Visualizer has significant functionality issues affecting 3 out of 4 main pages. The **Overview page works well**, the **Maps Performance tab works well**, but **Matches, Players (Rankings, Head-to-Head, Trends), and Territory Analysis are all critically broken** due to dropdown population failures and filter configuration issues.

The root causes appear to be:
1. Dropdown callback functions not populating options correctly
2. Overly restrictive default filter value (minimum matches: 3)
3. Missing or misconfigured score data in the database

**Immediate Action Required:** Fix the dropdown population logic and adjust the minimum matches filter default to restore basic functionality to the broken pages.
