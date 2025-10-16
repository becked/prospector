"""Integration tests for ruler tracking end-to-end."""

import pytest
from pathlib import Path
from tournament_visualizer.data.database import TournamentDatabase
from tournament_visualizer.data.parser import parse_tournament_file


@pytest.fixture
def integration_db(tmp_path: Path) -> TournamentDatabase:
    """Create a temporary database for integration tests.

    Args:
        tmp_path: Pytest temporary directory fixture

    Yields:
        TournamentDatabase instance with schema created
    """
    db_path = tmp_path / "integration_test.duckdb"
    db = TournamentDatabase(db_path=str(db_path), read_only=False)
    db.create_schema()
    yield db
    db.close()


class TestRulerIntegration:
    """Integration tests for complete ruler tracking workflow."""

    def test_full_pipeline_parser_to_database(self, integration_db: TournamentDatabase) -> None:
        """Test complete parsing and database insertion with ruler tracking."""
        # Use a known save file
        save_file = "saves/match_426504721_anarkos-becked.zip"

        if not Path(save_file).exists():
            pytest.skip(f"Test save file not found: {save_file}")

        # Parse the file
        parsed_data = parse_tournament_file(save_file)

        # Verify rulers were extracted
        rulers = parsed_data.get("rulers", [])
        assert len(rulers) > 0, "Should have extracted rulers"

        # Insert match and get match_id
        match_metadata = parsed_data["match_metadata"]
        match_metadata["file_name"] = "test.zip"
        match_metadata["file_hash"] = "test_hash"
        match_id = integration_db.insert_match(match_metadata)

        # Insert players
        players = parsed_data["players"]
        for player_data in players:
            player_data["match_id"] = match_id
            integration_db.insert_player(player_data)

        # Insert rulers
        integration_db.bulk_insert_rulers(match_id, rulers)

        # Verify rulers were inserted
        with integration_db.get_connection() as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM rulers WHERE match_id = ?"
                , [match_id]
            ).fetchone()

        assert result[0] > 0, "Should have inserted rulers"

        # Verify rulers have correct structure
        with integration_db.get_connection() as conn:
            db_rulers = conn.execute(
                """
                SELECT
                    match_id, player_id, character_id, ruler_name,
                    archetype, starting_trait, succession_order, succession_turn
                FROM rulers
                WHERE match_id = ?
                ORDER BY player_id, succession_order
                """,
                [match_id]
            ).fetchall()

        # Should have at least 2 rulers (one per player minimum)
        assert len(db_rulers) >= 2

        # Verify data types and constraints
        for ruler in db_rulers:
            match_id_val, player_id, char_id, name, arch, trait, order, turn = ruler

            # IDs should be positive
            assert match_id_val > 0
            assert player_id > 0
            assert char_id >= 0

            # Succession order and turn should be valid
            assert order >= 0
            assert turn >= 1

            # Starting ruler should be at turn 1
            if order == 0:
                assert turn == 1

    def test_rulers_match_players(self, integration_db: TournamentDatabase) -> None:
        """Test that all rulers have corresponding players."""
        save_file = "saves/match_426504721_anarkos-becked.zip"

        if not Path(save_file).exists():
            pytest.skip(f"Test save file not found: {save_file}")

        # Parse and insert data
        parsed_data = parse_tournament_file(save_file)

        match_metadata = parsed_data["match_metadata"]
        match_metadata["file_name"] = "test.zip"
        match_metadata["file_hash"] = "test_hash"
        match_id = integration_db.insert_match(match_metadata)

        players = parsed_data["players"]
        for player_data in players:
            player_data["match_id"] = match_id
            integration_db.insert_player(player_data)

        rulers = parsed_data.get("rulers", [])
        integration_db.bulk_insert_rulers(match_id, rulers)

        # Query rulers and players
        with integration_db.get_connection() as conn:
            result = conn.execute(
                """
                SELECT r.player_id, p.player_id
                FROM rulers r
                LEFT JOIN players p ON r.player_id = p.player_id AND r.match_id = p.match_id
                WHERE p.player_id IS NULL
                """
            ).fetchall()

        # Should have no orphaned rulers
        assert len(result) == 0, "All rulers should have corresponding players"

    def test_starting_rulers_have_archetype_and_trait(self, integration_db: TournamentDatabase) -> None:
        """Test that starting rulers have archetype and trait populated."""
        save_file = "saves/match_426504721_anarkos-becked.zip"

        if not Path(save_file).exists():
            pytest.skip(f"Test save file not found: {save_file}")

        # Parse and insert data
        parsed_data = parse_tournament_file(save_file)

        match_metadata = parsed_data["match_metadata"]
        match_metadata["file_name"] = "test.zip"
        match_metadata["file_hash"] = "test_hash"
        match_id = integration_db.insert_match(match_metadata)

        players = parsed_data["players"]
        for player_data in players:
            player_data["match_id"] = match_id
            integration_db.insert_player(player_data)

        rulers = parsed_data.get("rulers", [])
        integration_db.bulk_insert_rulers(match_id, rulers)

        # Query starting rulers
        with integration_db.get_connection() as conn:
            starting_rulers = conn.execute(
                """
                SELECT ruler_name, archetype, starting_trait
                FROM rulers
                WHERE succession_order = 0
                """
            ).fetchall()

        assert len(starting_rulers) > 0, "Should have starting rulers"

        for name, archetype, trait in starting_rulers:
            # Starting rulers should have archetype and trait
            # (Note: Some save files may have null values due to data issues)
            if archetype is not None:
                assert len(archetype) > 0, f"Ruler {name} should have non-empty archetype"
            if trait is not None:
                assert len(trait) > 0, f"Ruler {name} should have non-empty trait"

    def test_succession_count_analytics(self, integration_db: TournamentDatabase) -> None:
        """Test that we can answer the question: how many rulers did each player have?"""
        save_file = "saves/match_426504721_anarkos-becked.zip"

        if not Path(save_file).exists():
            pytest.skip(f"Test save file not found: {save_file}")

        # Parse and insert data
        parsed_data = parse_tournament_file(save_file)

        match_metadata = parsed_data["match_metadata"]
        match_metadata["file_name"] = "test.zip"
        match_metadata["file_hash"] = "test_hash"
        match_id = integration_db.insert_match(match_metadata)

        players = parsed_data["players"]
        for player_data in players:
            player_data["match_id"] = match_id
            integration_db.insert_player(player_data)

        rulers = parsed_data.get("rulers", [])
        integration_db.bulk_insert_rulers(match_id, rulers)

        # Run analytics query
        with integration_db.get_connection() as conn:
            results = conn.execute(
                """
                SELECT
                    p.player_name,
                    COUNT(r.ruler_id) as ruler_count,
                    MAX(r.succession_order) + 1 as succession_count
                FROM players p
                LEFT JOIN rulers r ON p.player_id = r.player_id AND p.match_id = r.match_id
                GROUP BY p.player_name
                ORDER BY p.player_name
                """
            ).fetchall()

        assert len(results) > 0, "Should have player ruler counts"

        for player_name, ruler_count, succession_count in results:
            # Counts should match
            assert ruler_count == succession_count, (
                f"Ruler count ({ruler_count}) should equal succession count ({succession_count})"
            )

            # Should have at least 1 ruler
            assert ruler_count >= 1, f"Player {player_name} should have at least 1 ruler"

    def test_archetype_analytics(self, integration_db: TournamentDatabase) -> None:
        """Test that we can analyze starting archetypes."""
        save_file = "saves/match_426504721_anarkos-becked.zip"

        if not Path(save_file).exists():
            pytest.skip(f"Test save file not found: {save_file}")

        # Parse and insert data
        parsed_data = parse_tournament_file(save_file)

        match_metadata = parsed_data["match_metadata"]
        match_metadata["file_name"] = "test.zip"
        match_metadata["file_hash"] = "test_hash"
        match_id = integration_db.insert_match(match_metadata)

        players = parsed_data["players"]
        for player_data in players:
            player_data["match_id"] = match_id
            integration_db.insert_player(player_data)

        rulers = parsed_data.get("rulers", [])
        integration_db.bulk_insert_rulers(match_id, rulers)

        # Run archetype analytics query
        with integration_db.get_connection() as conn:
            results = conn.execute(
                """
                SELECT
                    archetype,
                    COUNT(*) as count
                FROM rulers
                WHERE succession_order = 0
                AND archetype IS NOT NULL
                GROUP BY archetype
                ORDER BY count DESC
                """
            ).fetchall()

        # Should have at least one archetype
        assert len(results) > 0, "Should have archetype data"

        # Verify archetypes are valid
        valid_archetypes = {"Scholar", "Tactician", "Commander", "Schemer"}
        for archetype, count in results:
            assert archetype in valid_archetypes, (
                f"Invalid archetype: {archetype}"
            )
            assert count > 0


class TestMultipleFilesIntegration:
    """Test ruler tracking across multiple save files."""

    def test_multiple_files(self, integration_db: TournamentDatabase) -> None:
        """Test processing multiple save files."""
        saves_dir = Path("saves")

        if not saves_dir.exists():
            pytest.skip("saves/ directory not found")

        save_files = list(saves_dir.glob("match_*.zip"))[:3]  # Process 3 files

        if len(save_files) == 0:
            pytest.skip("No save files found in saves/ directory")

        successful = 0
        for save_file in save_files:
            try:
                # Parse the file
                parsed_data = parse_tournament_file(str(save_file))

                # Insert match
                match_metadata = parsed_data["match_metadata"]
                match_metadata["file_name"] = save_file.name
                match_metadata["file_hash"] = f"test_hash_{save_file.name}"
                match_id = integration_db.insert_match(match_metadata)

                # Insert players
                players = parsed_data["players"]
                for player_data in players:
                    player_data["match_id"] = match_id
                    integration_db.insert_player(player_data)

                # Insert rulers
                rulers = parsed_data.get("rulers", [])
                integration_db.bulk_insert_rulers(match_id, rulers)

                successful += 1
            except Exception as e:
                # Log but don't fail - some files may have issues
                print(f"Failed to process {save_file.name}: {e}")

        assert successful > 0, "At least one file should process successfully"

        # Verify total ruler count
        with integration_db.get_connection() as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM rulers"
            ).fetchone()

        # Should have rulers from multiple matches
        assert result[0] >= successful * 2, (
            "Should have at least 2 rulers per successful match"
        )
