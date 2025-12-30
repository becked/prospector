"""Tests for match timeline query function.

Test Strategy:
- Test event types are returned correctly (tech, law, city, ruler, death, battle, wonder)
- Test filtering of bonus techs and succession laws
- Test law swap detection
- Test UU unlock detection
- Test edge cases (single ruler, no military history, etc.)
"""

import pytest
import pandas as pd

from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.queries import TournamentQueries


class TestMatchTimelineEvents:
    """Test get_match_timeline_events() query function."""

    @pytest.fixture
    def timeline_test_db(self, tmp_path):
        """Create database with sample event data for timeline testing."""
        db_path = tmp_path / "timeline_test.duckdb"

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
            VALUES ('1', 'Initial schema')
        """)
        conn.close()

        db = TournamentDatabase(str(db_path), read_only=False)
        db.create_schema()

        with db.get_connection() as conn:
            # Insert match
            conn.execute("""
                INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash, total_turns)
                VALUES (1, 100, 'm1.zip', 'h1', 100)
            """)

            # Insert players
            conn.execute("""
                INSERT INTO players (player_id, match_id, player_name, player_name_normalized)
                VALUES
                (1, 1, 'player1', 'player1'),
                (2, 1, 'player2', 'player2')
            """)

            # Insert tech events
            conn.execute("""
                INSERT INTO events (event_id, match_id, turn_number, event_type, player_id, description, event_data)
                VALUES
                (1, 1, 1, 'TECH_DISCOVERED', 1, 'Discovered Ironworking', '{"tech":"TECH_IRONWORKING"}'),
                (2, 1, 1, 'TECH_DISCOVERED', 2, 'Discovered Polis', '{"tech":"TECH_POLIS"}'),
                (3, 1, 5, 'TECH_DISCOVERED', 1, 'Discovered Trapping', '{"tech":"TECH_TRAPPING"}'),
                (4, 1, 5, 'TECH_DISCOVERED', 1, 'Bonus tech', '{"tech":"TECH_IRONWORKING_BONUS_CIVICS"}')
            """)

            # Insert law events
            conn.execute("""
                INSERT INTO events (event_id, match_id, turn_number, event_type, player_id, description, event_data)
                VALUES
                (10, 1, 10, 'LAW_ADOPTED', 1, 'Adopted Freedom', '{"law":"LAW_FREEDOM"}'),
                (11, 1, 15, 'LAW_ADOPTED', 1, 'Adopted Centralization', '{"law":"LAW_CENTRALIZATION"}'),
                (12, 1, 20, 'LAW_ADOPTED', 1, 'Adopted Serfdom', '{"law":"LAW_SERFDOM"}'),
                (13, 1, 25, 'LAW_ADOPTED', 1, 'Adopted Monotheism', '{"law":"LAW_MONOTHEISM"}'),
                (14, 1, 30, 'LAW_ADOPTED', 1, 'Adopted Primogeniture', '{"law":"LAW_PRIMOGENITURE"}'),
                (15, 1, 35, 'LAW_ADOPTED', 2, 'Adopted Slavery', '{"law":"LAW_SLAVERY"}'),
                (16, 1, 40, 'LAW_ADOPTED', 2, 'Adopted Freedom', '{"law":"LAW_FREEDOM"}')
            """)

            # Insert city events
            conn.execute("""
                INSERT INTO events (event_id, match_id, turn_number, event_type, player_id, description, event_data)
                VALUES
                (20, 1, 1, 'CITY_FOUNDED', 1, 'Founded  Roma', NULL),
                (21, 1, 1, 'CITY_FOUNDED', 2, 'Founded  Athens', NULL),
                (22, 1, 12, 'CITY_FOUNDED', 1, 'Founded  Milano', NULL)
            """)

            # Insert cities table for capital detection
            conn.execute("""
                INSERT INTO cities (city_id, match_id, player_id, city_name, tile_id, founded_turn, is_capital)
                VALUES
                (0, 1, 1, 'Roma', 100, 1, TRUE),
                (1, 1, 2, 'Athens', 200, 1, TRUE),
                (2, 1, 1, 'Milano', 300, 12, FALSE)
            """)

            # Insert rulers
            conn.execute("""
                INSERT INTO rulers (ruler_id, match_id, player_id, character_id, ruler_name, archetype, starting_trait, succession_order, succession_turn)
                VALUES
                (1, 1, 1, 1, 'Augustus', 'Commander', 'Brave', 0, 1),
                (2, 1, 1, 2, 'Tiberius', 'Scholar', NULL, 1, 45),
                (3, 1, 2, 3, 'Pericles', 'Diplomat', 'Wise', 0, 1)
            """)

            # Insert military history (for battle detection)
            conn.execute("""
                INSERT INTO player_military_history (military_history_id, match_id, player_id, turn_number, military_power)
                VALUES
                (1, 1, 1, 50, 100),
                (2, 1, 1, 51, 100),
                (3, 1, 1, 52, 75),
                (4, 1, 1, 53, 70),
                (5, 1, 2, 50, 80),
                (6, 1, 2, 51, 80),
                (7, 1, 2, 52, 80)
            """)

            # Insert wonder events (with duplicates as they appear in game)
            conn.execute("""
                INSERT INTO events (event_id, match_id, turn_number, event_type, player_id, description, event_data)
                VALUES
                (30, 1, 20, 'WONDER_ACTIVITY', 1, ' Rome (player1) has begun construction of The Pyramids.', NULL),
                (31, 1, 20, 'WONDER_ACTIVITY', 2, ' Rome (player1) has begun construction of The Pyramids.', NULL),
                (32, 1, 30, 'WONDER_ACTIVITY', 1, 'The Pyramids completed by  Rome (player1)!', NULL),
                (33, 1, 30, 'WONDER_ACTIVITY', 2, 'The Pyramids completed by  Rome (player1)!', NULL)
            """)

        yield db
        db.close()

    def test_tech_events_returned(self, timeline_test_db: TournamentDatabase) -> None:
        """Tech discoveries appear in timeline with correct type."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        tech_events = df[df["event_type"] == "tech"]
        assert len(tech_events) >= 3  # Should have at least 3 non-bonus techs

        # Check title formatting (should include "Discovered:" prefix)
        ironworking = tech_events[tech_events["title"] == "Discovered: Ironworking"]
        assert len(ironworking) > 0

    def test_tech_bonus_variants_filtered(self, timeline_test_db: TournamentDatabase) -> None:
        """_BONUS_ tech variants are excluded from timeline."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        # Check that no bonus techs appear
        bonus_techs = df[df["title"].str.contains("BONUS", case=False, na=False)]
        assert len(bonus_techs) == 0

    def test_law_events_returned(self, timeline_test_db: TournamentDatabase) -> None:
        """Law adoptions appear in timeline."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        law_events = df[df["event_type"].isin(["law", "law_swap"])]
        # Should have laws (excluding primogeniture)
        assert len(law_events) >= 5

    def test_succession_laws_ignored(self, timeline_test_db: TournamentDatabase) -> None:
        """Succession laws (primogeniture, seniority, ultimogeniture) excluded."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        # Primogeniture should not appear
        primo = df[df["title"].str.lower().str.contains("primogeniture", na=False)]
        assert len(primo) == 0

    def test_law_swap_detection(self, timeline_test_db: TournamentDatabase) -> None:
        """Consecutive laws in same class marked as swap."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        # Player 2 adopts Slavery (t35) then Freedom (t40) - same class
        swap_events = df[df["event_type"] == "law_swap"]
        assert len(swap_events) >= 1

        # The swap should show arrow notation
        freedom_swap = swap_events[swap_events["title"].str.contains("→", na=False)]
        assert len(freedom_swap) >= 1

    def test_city_founding_events(self, timeline_test_db: TournamentDatabase) -> None:
        """City founding from CITY_FOUNDED events appears in timeline."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        city_events = df[df["event_type"].isin(["city", "capital"])]
        assert len(city_events) >= 3

    def test_capital_distinct_from_city(self, timeline_test_db: TournamentDatabase) -> None:
        """Capital uses different event_type than regular city."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        # Turn 1 cities should be capitals
        capitals = df[(df["event_type"] == "capital") & (df["turn"] == 1)]
        assert len(capitals) >= 2

        # Turn 12 city should be regular city
        regular_cities = df[(df["event_type"] == "city") & (df["turn"] == 12)]
        assert len(regular_cities) >= 1

    def test_ruler_succession_events(self, timeline_test_db: TournamentDatabase) -> None:
        """Ruler successions appear in timeline."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        ruler_events = df[df["event_type"] == "ruler"]
        # Should have 3 rulers (2 for player 1, 1 for player 2)
        assert len(ruler_events) == 3

        # Check title formatting (starting ruler vs crowned)
        augustus = ruler_events[ruler_events["title"] == "Starting Ruler: Augustus"]
        assert len(augustus) == 1
        assert "Commander" in augustus.iloc[0]["details"]

        # Non-starting ruler should use "Crowned" prefix
        tiberius = ruler_events[ruler_events["title"] == "Crowned Tiberius"]
        assert len(tiberius) == 1

    def test_ruler_death_inferred(self, timeline_test_db: TournamentDatabase) -> None:
        """Ruler death inferred from next succession_turn."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        death_events = df[df["event_type"] == "death"]
        # Player 1's first ruler dies on same turn as successor is crowned (turn 45)
        assert len(death_events) == 1
        assert death_events.iloc[0]["turn"] == 45
        assert death_events.iloc[0]["title"] == "Augustus Died"

    def test_battle_detection_threshold(self, timeline_test_db: TournamentDatabase) -> None:
        """Military power drops >= 20% flagged as battles."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        battle_events = df[df["event_type"] == "battle"]
        # Player 1 drops from 100 to 75 at turn 52 (25% drop)
        assert len(battle_events) >= 1

        # Check details show percentage
        assert any("%" in str(d) for d in battle_events["details"])

    def test_no_battle_below_threshold(self, timeline_test_db: TournamentDatabase) -> None:
        """Military drops < 20% not flagged as battles."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        # Player 2 has no significant drops
        p2_battles = df[(df["event_type"] == "battle") & (df["player_id"] == 2)]
        assert len(p2_battles) == 0

    def test_uu_unlock_on_4th_law(self, timeline_test_db: TournamentDatabase) -> None:
        """UU unlock event generated on 4th law adoption."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        uu_events = df[df["event_type"] == "uu_unlock"]
        # Player 1 has 4 non-succession laws, should get 6 strength UU unlock
        assert len(uu_events) >= 1
        assert any("6 Strength" in str(t) for t in uu_events["title"])

    def test_timeline_sorted_by_turn(self, timeline_test_db: TournamentDatabase) -> None:
        """Timeline events sorted by turn, then player_id."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        # Check turns are sorted
        turns = df["turn"].tolist()
        assert turns == sorted(turns)

    def test_empty_match_returns_empty_dataframe(
        self, timeline_test_db: TournamentDatabase
    ) -> None:
        """Match with no events returns empty DataFrame with correct columns."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=999)  # Non-existent match

        assert df.empty
        expected_cols = ["turn", "player_id", "event_type", "title", "details", "icon", "subtype"]
        for col in expected_cols:
            assert col in df.columns

    def test_wonder_started_english(self, timeline_test_db: TournamentDatabase) -> None:
        """English 'begun construction' parsed as wonder_start."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        wonder_start = df[(df["event_type"] == "wonder_start") & (df["turn"] == 20)]
        assert len(wonder_start) >= 1
        assert "Pyramids" in wonder_start.iloc[0]["title"]

    def test_wonder_completed_english(self, timeline_test_db: TournamentDatabase) -> None:
        """English 'completed' parsed as wonder_complete."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        wonder_complete = df[(df["event_type"] == "wonder_complete") & (df["turn"] == 30)]
        assert len(wonder_complete) >= 1

    def test_wonder_events_deduplicated(self, timeline_test_db: TournamentDatabase) -> None:
        """Duplicate wonder events (one per observer) are deduplicated."""
        queries = TournamentQueries(timeline_test_db)
        df = queries.get_match_timeline_events(match_id=1)

        # Should only have 1 wonder_start and 1 wonder_complete, not 2 of each
        wonder_starts = df[(df["event_type"] == "wonder_start") & (df["turn"] == 20)]
        assert len(wonder_starts) == 1

        wonder_completes = df[(df["event_type"] == "wonder_complete") & (df["turn"] == 30)]
        assert len(wonder_completes) == 1


class TestTimelineEdgeCases:
    """Test edge cases for timeline query."""

    @pytest.fixture
    def edge_case_db(self, tmp_path):
        """Create database with edge case data."""
        db_path = tmp_path / "edge_case_test.duckdb"

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
            VALUES ('1', 'Initial schema')
        """)
        conn.close()

        db = TournamentDatabase(str(db_path), read_only=False)
        db.create_schema()

        with db.get_connection() as conn:
            # Insert match
            conn.execute("""
                INSERT INTO matches (match_id, challonge_match_id, file_name, file_hash, total_turns)
                VALUES (1, 100, 'm1.zip', 'h1', 50)
            """)

            # Insert player
            conn.execute("""
                INSERT INTO players (player_id, match_id, player_name, player_name_normalized)
                VALUES (1, 1, 'player1', 'player1')
            """)

            # Only one ruler (no death should be generated)
            conn.execute("""
                INSERT INTO rulers (ruler_id, match_id, player_id, character_id, ruler_name, archetype, starting_trait, succession_order, succession_turn)
                VALUES (1, 1, 1, 1, 'Solo Ruler', 'Commander', 'Brave', 0, 1)
            """)

            # Only 3 laws (no UU unlock should be generated)
            conn.execute("""
                INSERT INTO events (event_id, match_id, turn_number, event_type, player_id, description, event_data)
                VALUES
                (1, 1, 10, 'LAW_ADOPTED', 1, 'Adopted Freedom', '{"law":"LAW_FREEDOM"}'),
                (2, 1, 20, 'LAW_ADOPTED', 1, 'Adopted Centralization', '{"law":"LAW_CENTRALIZATION"}'),
                (3, 1, 30, 'LAW_ADOPTED', 1, 'Adopted Serfdom', '{"law":"LAW_SERFDOM"}')
            """)

        yield db
        db.close()

    def test_single_ruler_no_death_event(self, edge_case_db: TournamentDatabase) -> None:
        """Match with only one ruler doesn't generate death event."""
        queries = TournamentQueries(edge_case_db)
        df = queries.get_match_timeline_events(match_id=1)

        death_events = df[df["event_type"] == "death"]
        assert len(death_events) == 0

    def test_no_military_history_no_battles(self, edge_case_db: TournamentDatabase) -> None:
        """Match without military history returns no battle events."""
        queries = TournamentQueries(edge_case_db)
        df = queries.get_match_timeline_events(match_id=1)

        battle_events = df[df["event_type"] == "battle"]
        assert len(battle_events) == 0

    def test_fewer_than_4_laws_no_uu(self, edge_case_db: TournamentDatabase) -> None:
        """Player with fewer than 4 laws gets no UU unlock."""
        queries = TournamentQueries(edge_case_db)
        df = queries.get_match_timeline_events(match_id=1)

        uu_events = df[df["event_type"] == "uu_unlock"]
        assert len(uu_events) == 0
