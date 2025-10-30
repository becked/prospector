# Refactor City Queries for Codebase Consistency

## Overview

The city data implementation (Tasks 4-7 from the original plan) introduced standalone query functions that deviate from the existing codebase pattern. This refactoring aligns city queries with the established architecture: class-based methods in `TournamentQueries` that use the database abstraction layer.

**Problem**: Current city queries are standalone functions using direct DuckDB connections, while all other queries are class methods using `self.db`.

**Solution**: Convert standalone functions to class methods, update tests to match existing patterns.

**Benefits**:
- Architectural consistency across the codebase
- Uses existing database abstraction layer (threading-safe, connection pooling)
- Matches test patterns used throughout the project
- Easier maintenance (one pattern to understand)

---

## Task 0: Discovery & Pattern Analysis

### Existing Query Patterns

**File**: `tournament_visualizer/data/queries.py`

**Structure**: Class-based architecture
- **Class**: `TournamentQueries` (line 14)
- **Constructor**: Takes optional `TournamentDatabase` instance (line 17)
- **Pattern**: `self.db = database or get_database()` (line 23)

**Return Types**:
- **DataFrames**: Most methods return `pd.DataFrame` (lines 25, 75, 189, etc.)
  - Example: `get_match_summary()` at line 25
  - Example: `get_player_performance()` at line 75
- **List[str]**: `get_opponents()` at line 250
- **Dict[str, Any]**: `get_head_to_head_stats()` at line 315

**Database Access Pattern**:
```python
# Pattern for DataFrame (line 72-73):
with self.db.get_connection() as conn:
    return conn.execute(query).df()

# Pattern for List (line 307-313):
with self.db.get_connection() as conn:
    result = conn.execute(query, params).fetchall()
return [row[0] for row in result]

# Pattern for Dict (line 438-450):
with self.db.get_connection() as conn:
    result = conn.execute(query, params).fetchone()
if result:
    return {"key": result[0], "key2": result[1], ...}
return {}
```

### Existing Test Patterns

**File**: `tests/test_queries_civilization_performance.py`

**Structure**: pytest with fixtures and class-based tests
- **Fixture**: Creates `TournamentDatabase` instance (line 10-69)
  - Uses `tmp_path` for isolation
  - Creates schema with `db.create_schema()`
  - Populates test data
  - Returns `TournamentDatabase` instance
  - Cleans up after test

**Test Pattern** (line 75-88):
```python
def test_something(self, civ_test_db):
    queries = TournamentQueries(civ_test_db)  # Pass database to constructor
    df = queries.get_civilization_performance()  # Call method
    assert df['column'] == expected_value  # Assert on DataFrame
```

### Current City Query Deviations

**File**: `tournament_visualizer/data/queries.py` (lines 2699-2844)

**Deviations**:
1. ❌ Standalone functions instead of class methods
2. ❌ Take `db_path: str` parameter instead of using `self.db`
3. ❌ Create direct DuckDB connections: `duckdb.connect(db_path, read_only=True)`
4. ❌ Return `List[Dict[str, Any]]` instead of `pd.DataFrame`
5. ❌ Manual row-to-dict conversion instead of `.df()`

**Example of current deviation**:
```python
# ❌ CURRENT (standalone function)
def get_match_cities(match_id: int, db_path: str = "data/tournament_data.duckdb") -> List[Dict[str, Any]]:
    import duckdb
    conn = duckdb.connect(db_path, read_only=True)
    result = conn.execute(query, [match_id]).fetchall()
    conn.close()
    cities = []
    for row in result:
        cities.append({'city_id': row[0], 'city_name': row[1], ...})
    return cities
```

### Architecture Decision

**Decision**: Refactor to follow existing class-based pattern

**Rationale**:
- **Consistency**: All other queries use class methods
- **DRY**: Reuse existing database abstraction (connection pooling, thread safety)
- **Maintainability**: One pattern to learn and maintain
- **Testing**: Match existing test fixture patterns
- **Return type**: Use DataFrames like 90% of other queries (more consistent with pandas-heavy codebase)

**No compelling reason to deviate** - city queries are similar to other queries and benefit from the same abstractions.

---

## Task 1: Refactor Query Functions to Class Methods (1 hour)

### Subtask 1.1: Convert `get_match_cities()` to Class Method

**File**: `tournament_visualizer/data/queries.py`

**Why this approach**: Follows pattern from `get_turn_progression_data()` at line 524 (takes match_id, returns DataFrame)

**What to do**:

1. Find the standalone function `get_match_cities()` at approximately line 2699
2. Delete it entirely (including the column existence check logic)
3. Add as a method to `TournamentQueries` class (add before line 2694 where city functions start)

**Code to add**:
```python
    def get_match_cities(self, match_id: int) -> pd.DataFrame:
        """Get all cities for a specific match.

        Args:
            match_id: Tournament match ID

        Returns:
            DataFrame with columns:
                - city_id: City identifier
                - city_name: City name (e.g., 'CITYNAME_NINEVEH')
                - player_id: Current owner player ID
                - player_name: Current owner player name
                - founded_turn: Turn when city was founded
                - is_capital: Boolean, TRUE if capital city
                - population: City population (may be NULL)
                - tile_id: Map tile location
        """
        query = """
        SELECT
            c.city_id,
            c.city_name,
            c.player_id,
            p.player_name,
            c.founded_turn,
            c.is_capital,
            c.population,
            c.tile_id
        FROM cities c
        JOIN players p ON c.match_id = p.match_id AND c.player_id = p.player_id
        WHERE c.match_id = ?
        ORDER BY c.founded_turn, c.city_id
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()
```

**Test it**:
```bash
# This will fail because tests need updating - that's Task 2
uv run pytest tests/test_queries_cities.py::TestCityQueries::test_get_match_cities -v
```

**Expected output**: Import error or AttributeError (tests still use old interface)

**Commit Point**: ✓ "refactor: Convert get_match_cities to TournamentQueries class method"

---

### Subtask 1.2: Convert `get_player_expansion_stats()` to Class Method

**File**: `tournament_visualizer/data/queries.py`

**Why this approach**: Follows pattern from `get_player_performance()` at line 75 (aggregates player stats, returns DataFrame)

**What to do**:

1. Find the standalone function `get_player_expansion_stats()` at approximately line 2750
2. Delete it entirely
3. Add as a method to `TournamentQueries` class (after `get_match_cities()`)

**Code to add**:
```python
    def get_player_expansion_stats(self, match_id: int) -> pd.DataFrame:
        """Get expansion statistics for each player in a match.

        Args:
            match_id: Tournament match ID

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - total_cities: Total number of cities owned
                - first_city_turn: Turn when first city was founded
                - last_city_turn: Turn when last city was founded
                - capital_count: Number of capital cities
        """
        query = """
        SELECT
            p.player_id,
            p.player_name,
            COUNT(c.city_id) as total_cities,
            MIN(c.founded_turn) as first_city_turn,
            MAX(c.founded_turn) as last_city_turn,
            SUM(CASE WHEN c.is_capital THEN 1 ELSE 0 END) as capital_count
        FROM players p
        LEFT JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        WHERE p.match_id = ?
        GROUP BY p.player_id, p.player_name
        ORDER BY total_cities DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()
```

**Test it**:
```bash
uv run pytest tests/test_queries_cities.py::TestCityQueries::test_get_player_expansion_stats -v
```

**Expected output**: Import error or AttributeError (tests still use old interface)

**Commit Point**: ✓ "refactor: Convert get_player_expansion_stats to TournamentQueries class method"

---

### Subtask 1.3: Convert `get_production_summary()` to Class Method

**File**: `tournament_visualizer/data/queries.py`

**Why this approach**: Follows pattern from `get_player_performance()` at line 75 (aggregates player stats, returns DataFrame)

**What to do**:

1. Find the standalone function `get_production_summary()` at approximately line 2798
2. Delete it entirely
3. Add as a method to `TournamentQueries` class (after `get_player_expansion_stats()`)

**Code to add**:
```python
    def get_production_summary(self, match_id: int) -> pd.DataFrame:
        """Get unit production summary for each player.

        Args:
            match_id: Tournament match ID

        Returns:
            DataFrame with columns:
                - player_id: Player identifier
                - player_name: Player name
                - total_units_produced: Total units produced across all cities
                - unique_unit_types: Number of different unit types produced
                - settlers: Total settler units produced
                - workers: Total worker units produced
        """
        query = """
        SELECT
            p.player_id,
            p.player_name,
            COALESCE(SUM(prod.count), 0) as total_units_produced,
            COUNT(DISTINCT prod.unit_type) as unique_unit_types,
            COALESCE(SUM(CASE WHEN prod.unit_type = 'UNIT_SETTLER' THEN prod.count ELSE 0 END), 0) as settlers,
            COALESCE(SUM(CASE WHEN prod.unit_type = 'UNIT_WORKER' THEN prod.count ELSE 0 END), 0) as workers
        FROM players p
        LEFT JOIN cities c ON p.match_id = c.match_id AND p.player_id = c.player_id
        LEFT JOIN city_unit_production prod ON c.match_id = prod.match_id AND c.city_id = prod.city_id
        WHERE p.match_id = ?
        GROUP BY p.player_id, p.player_name
        ORDER BY total_units_produced DESC
        """

        with self.db.get_connection() as conn:
            return conn.execute(query, [match_id]).df()
```

**Test it**:
```bash
uv run pytest tests/test_queries_cities.py::TestCityQueries::test_get_production_summary -v
```

**Expected output**: Import error or AttributeError (tests still use old interface)

**Commit Point**: ✓ "refactor: Convert get_production_summary to TournamentQueries class method"

---

## Task 2: Update Tests to Match Existing Patterns (45 min)

### Subtask 2.1: Refactor Test Fixtures

**File**: `tests/test_queries_cities.py`

**Why this approach**: Follows pattern from `tests/test_queries_civilization_performance.py` at line 10

**What to do**:

1. Replace the entire `temp_db_with_city_data` fixture (approximately line 21-99)
2. Use the same pattern as other query tests: create `TournamentDatabase`, populate data, return database instance

**Code to replace**:
```python
import pytest

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


class TestCityQueries:
    """Test query functions for city data."""

    @pytest.fixture
    def city_test_db(self, tmp_path):
        """Create database with sample city data.

        Follows pattern from test_queries_civilization_performance.py fixture.
        """
        db_path = tmp_path / "city_test.duckdb"

        # Create database with schema
        import duckdb
        conn = duckdb.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(20) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        conn.execute("""
            INSERT INTO schema_migrations (version, description)
            VALUES ('5', 'Add city tracking tables')
        """)
        conn.close()

        db = TournamentDatabase(str(db_path), read_only=False)
        db.create_schema()

        with db.get_connection() as conn:
            # Insert matches
            conn.execute("""
                INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash, total_turns)
                VALUES
                (1, 100, 'm1.zip', 'h1', 92),
                (2, 101, 'm2.zip', 'h2', 47)
            """)

            # Insert players
            conn.execute("""
                INSERT INTO players (player_id, match_id, player_name, player_name_normalized)
                VALUES
                (1, 1, 'anarkos', 'anarkos'),
                (2, 1, 'becked', 'becked'),
                (1, 2, 'moose', 'moose'),
                (2, 2, 'fluffbunny', 'fluffbunny')
            """)

            # Insert cities
            conn.execute("""
                INSERT INTO cities (city_id, match_id, player_id, city_name, tile_id, founded_turn, is_capital)
                VALUES
                (0, 1, 1, 'CITYNAME_NINEVEH', 100, 1, TRUE),
                (1, 1, 2, 'CITYNAME_PERSEPOLIS', 200, 1, TRUE),
                (2, 1, 1, 'CITYNAME_SAREISA', 300, 15, FALSE),
                (3, 1, 2, 'CITYNAME_ARBELA', 400, 22, FALSE),
                (0, 2, 1, 'CITYNAME_CAPITAL1', 500, 1, TRUE),
                (1, 2, 2, 'CITYNAME_CAPITAL2', 600, 1, TRUE)
            """)

            # Insert city unit production
            conn.execute("""
                INSERT INTO city_unit_production (match_id, city_id, unit_type, count)
                VALUES
                (1, 0, 'UNIT_SETTLER', 4),
                (1, 0, 'UNIT_WORKER', 1),
                (1, 0, 'UNIT_SPEARMAN', 3),
                (1, 1, 'UNIT_SETTLER', 3),
                (1, 1, 'UNIT_ARCHER', 5)
            """)

        yield db
        db.close()
```

**Test it**:
```bash
# Should fail because tests still use old assertions
uv run pytest tests/test_queries_cities.py -v
```

**Expected output**: Tests run but assertions fail (DataFrame vs dict comparison)

**Commit Point**: ✓ "test: Update city query test fixtures to use TournamentDatabase"

---

### Subtask 2.2: Update Test Methods

**File**: `tests/test_queries_cities.py`

**Why this approach**: Follows pattern from `tests/test_queries_civilization_performance.py` at line 75

**What to do**:

1. Update each test method to:
   - Accept `city_test_db` fixture (not `temp_db_with_city_data`)
   - Create `TournamentQueries` instance with database
   - Call method (not function)
   - Assert on DataFrame columns (not dict keys)

**Code to replace** (approximately line 101-160):
```python
    def test_get_match_cities(self, city_test_db: TournamentDatabase) -> None:
        """Test getting all cities for a match."""
        queries = TournamentQueries(city_test_db)

        df = queries.get_match_cities(match_id=1)

        # Should have 4 cities for match 1
        assert len(df) == 4

        # Check first city (Nineveh)
        first_city = df.iloc[0]
        assert first_city['city_name'] == 'CITYNAME_NINEVEH'
        assert first_city['founded_turn'] == 1
        assert first_city['is_capital'] is True

    def test_get_player_expansion_stats(self, city_test_db: TournamentDatabase) -> None:
        """Test expansion statistics for a match."""
        queries = TournamentQueries(city_test_db)

        df = queries.get_player_expansion_stats(match_id=1)

        # Should have stats for 2 players
        assert len(df) == 2

        # Check player 1 (anarkos) - should have 2 cities
        player1 = df[df['player_name'] == 'anarkos'].iloc[0]
        assert player1['total_cities'] == 2
        assert player1['first_city_turn'] == 1
        assert player1['last_city_turn'] == 15

        # Check player 2 (becked) - should have 2 cities
        player2 = df[df['player_name'] == 'becked'].iloc[0]
        assert player2['total_cities'] == 2
        assert player2['last_city_turn'] == 22

    def test_get_production_summary(self, city_test_db: TournamentDatabase) -> None:
        """Test production summary by player."""
        queries = TournamentQueries(city_test_db)

        df = queries.get_production_summary(match_id=1)

        # Should have summary for 2 players
        assert len(df) == 2

        # Check player 1 (anarkos) - produced 4+1+3=8 units
        player1 = df[df['player_id'] == 1].iloc[0]
        assert player1['total_units_produced'] == 8
        assert player1['settlers'] == 4
        assert player1['workers'] == 1

        # Check player 2 (becked) - produced 3+5=8 units
        player2 = df[df['player_id'] == 2].iloc[0]
        assert player2['total_units_produced'] == 8
        assert player2['settlers'] == 3
```

**Test it**:
```bash
uv run pytest tests/test_queries_cities.py -v
```

**Expected output**: All tests pass ✓

**Commit Point**: ✓ "test: Update city query tests to use class methods and DataFrames"

---

## Task 3: Update Documentation (15 min)

### Subtask 3.1: Update CLAUDE.md Examples

**File**: `CLAUDE.md`

**Why this approach**: Documentation should show users the actual API

**What to do**:

1. Find the "City Data Analysis" section (approximately line 222)
2. Update the "Querying City Data" subsection (approximately line 240-263)

**Code to replace**:
```markdown
### Querying City Data

```python
from tournament_visualizer.data.queries import TournamentQueries, get_queries

# Option 1: Use global queries instance
queries = get_queries()

# Option 2: Create instance with custom database
from tournament_visualizer.data.database import TournamentDatabase
db = TournamentDatabase("data/tournament_data.duckdb")
queries = TournamentQueries(db)

# Get all cities in a match (returns DataFrame)
cities_df = queries.get_match_cities(match_id=1)
for _, city in cities_df.iterrows():
    print(f"{city['city_name']} founded turn {city['founded_turn']}")

# Get expansion statistics (returns DataFrame)
stats_df = queries.get_player_expansion_stats(match_id=1)
for _, player in stats_df.iterrows():
    print(f"{player['player_name']}: {player['total_cities']} cities")

# Get production summary (returns DataFrame)
summary_df = queries.get_production_summary(match_id=1)
for _, player in summary_df.iterrows():
    print(f"{player['player_name']}: {player['settlers']} settlers")

# DataFrames can be easily converted for plotting or further analysis
import matplotlib.pyplot as plt
stats_df.plot(x='player_name', y='total_cities', kind='bar')
plt.show()
```
```

**Test it**:
```bash
# Verify examples work in Python REPL (after migration is run)
uv run python -c "
from tournament_visualizer.data.queries import get_queries
queries = get_queries()
print('✓ Import successful')
"
```

**Expected output**: `✓ Import successful`

**Commit Point**: ✓ "docs: Update city query examples to use class methods"

---

## Task 4: Verify Integration (30 min)

### Subtask 4.1: Run All Tests

**What to do**:
```bash
# Run city query tests
uv run pytest tests/test_queries_cities.py -v

# Run all query tests to ensure no regressions
uv run pytest tests/test_queries*.py -v

# Run full test suite
uv run pytest -v
```

**Expected output**: All tests pass ✓

**If tests fail**:
- Check that DataFrames have expected columns
- Verify query SQL syntax
- Ensure fixture data matches test expectations

---

### Subtask 4.2: Test with Real Database (Optional)

**What to do**:

Only if the migration has been run on the real database:

```bash
# Start Python REPL
uv run python

# Test queries
>>> from tournament_visualizer.data.queries import get_queries
>>> queries = get_queries()
>>>
>>> # Check if we have cities
>>> cities = queries.get_match_cities(match_id=1)
>>> print(f"Found {len(cities)} cities")
>>>
>>> # Check expansion stats
>>> stats = queries.get_player_expansion_stats(match_id=1)
>>> print(stats)
>>>
>>> # Check production
>>> prod = queries.get_production_summary(match_id=1)
>>> print(prod)
```

**Expected output**:
- DataFrames with city data
- No errors
- Data looks reasonable

**If queries fail**:
- Ensure migration was run: `uv run python scripts/migrate_add_city_tables.py`
- Ensure data was imported: `uv run python scripts/import_attachments.py --directory saves`

---

## Common Pitfalls

### Pitfall 1: Forgetting to Pass Database to Constructor

**Problem**: `TypeError: __init__() missing 1 required positional argument: 'database'`

**Solution**:
```python
# ❌ WRONG
queries = TournamentQueries()  # Uses global database - may not be test db

# ✅ CORRECT (in tests)
queries = TournamentQueries(city_test_db)
```

### Pitfall 2: Treating DataFrame Like List of Dicts

**Problem**: `KeyError` or `TypeError: 'DataFrame' object is not subscriptable`

**Solution**:
```python
# ❌ WRONG (old API)
cities = queries.get_match_cities(match_id=1)
for city in cities:  # cities is DataFrame, not list
    print(city['city_name'])  # ERROR

# ✅ CORRECT (new API)
cities_df = queries.get_match_cities(match_id=1)
for _, city in cities_df.iterrows():  # Iterate DataFrame
    print(city['city_name'])

# Or better: vectorized operations
city_names = cities_df['city_name'].tolist()
```

### Pitfall 3: Comparing DataFrame to Dict in Tests

**Problem**: `AssertionError` because `df['column']` is a Series, not a value

**Solution**:
```python
# ❌ WRONG
assert df['city_name'] == 'CITYNAME_NINEVEH'  # Compares Series to string

# ✅ CORRECT
assert df.iloc[0]['city_name'] == 'CITYNAME_NINEVEH'  # Get first row value
# Or
first_city = df[df['city_name'] == 'CITYNAME_NINEVEH'].iloc[0]
assert first_city['founded_turn'] == 1
```

### Pitfall 4: Not Cleaning Up Database in Fixture

**Problem**: Tests fail with "database is locked" or "file in use"

**Solution**:
```python
@pytest.fixture
def city_test_db(tmp_path):
    db = TournamentDatabase(...)
    # ... populate data ...
    yield db
    db.close()  # ← IMPORTANT: Clean up
```

---

## Success Criteria

You'll know the refactoring is complete when:

- [ ] All three city query functions are now methods on `TournamentQueries` class
- [ ] All methods use `self.db.get_connection()` pattern
- [ ] All methods return `pd.DataFrame`
- [ ] Tests use `TournamentDatabase` fixtures
- [ ] Tests instantiate `TournamentQueries(database)`
- [ ] All tests in `tests/test_queries_cities.py` pass
- [ ] All other query tests still pass (no regressions)
- [ ] Documentation shows class method usage
- [ ] No standalone query functions remain (except global `queries` instance)

**Final verification**:
```bash
# All tests pass
uv run pytest tests/test_queries_cities.py -v
uv run pytest tests/test_queries*.py -v

# Code style checks
uv run ruff check tournament_visualizer/data/queries.py
uv run black --check tournament_visualizer/data/queries.py

# Grep confirms no standalone functions
grep -n "^def get_match_cities" tournament_visualizer/data/queries.py
# Should return nothing (method, not function)

grep -n "def get_match_cities(self" tournament_visualizer/data/queries.py
# Should return line number (class method)
```

---

## Time Estimate

- Task 0: Discovery (not needed - already done in this plan): 0 min
- Task 1: Refactor functions to methods: 60 min
- Task 2: Update tests: 45 min
- Task 3: Update documentation: 15 min
- Task 4: Verify integration: 30 min

**Total**: ~2.5 hours

---

## Architecture Benefits After Refactoring

**Before** (inconsistent):
```python
# Query 1: Class method returning DataFrame
queries = TournamentQueries()
df = queries.get_match_summary()

# Query 2: Standalone function returning list of dicts
from tournament_visualizer.data.queries import get_match_cities
cities = get_match_cities(match_id=1, db_path="data.db")
```

**After** (consistent):
```python
# All queries: Class methods returning DataFrames
queries = TournamentQueries()
match_df = queries.get_match_summary()
cities_df = queries.get_match_cities(match_id=1)
stats_df = queries.get_player_expansion_stats(match_id=1)
```

**Wins**:
- ✅ One pattern to learn
- ✅ Easier to mock in tests (one object to mock, not multiple functions)
- ✅ DataFrames integrate better with pandas-heavy codebase
- ✅ Database abstraction handles threading and connection pooling
- ✅ Consistent with 40+ other query methods in the codebase
