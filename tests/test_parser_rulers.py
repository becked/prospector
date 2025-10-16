"""Tests for ruler extraction from Old World save files."""

import pytest
from tournament_visualizer.data.parser import OldWorldSaveParser


class TestExtractRulers:
    """Tests for the extract_rulers() method."""

    def test_extract_rulers_requires_parsed_xml(self) -> None:
        """Test that extract_rulers() raises ValueError if XML not parsed."""
        parser = OldWorldSaveParser("dummy.zip")

        with pytest.raises(ValueError, match="XML not parsed"):
            parser.extract_rulers()

    def test_extract_rulers_basic_structure(self) -> None:
        """Test that extract_rulers() returns expected structure."""
        # Use a known save file from the saves/ directory
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Should have rulers for both players
        assert len(rulers) > 0

        # Verify structure of first ruler
        ruler = rulers[0]
        assert "player_id" in ruler
        assert "character_id" in ruler
        assert "ruler_name" in ruler
        assert "archetype" in ruler
        assert "starting_trait" in ruler
        assert "succession_order" in ruler
        assert "succession_turn" in ruler

    def test_extract_rulers_player_id_mapping(self) -> None:
        """Test that player IDs are correctly converted from 0-based to 1-based."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Player IDs should be 1 and 2 (1-based), not 0 and 1 (0-based XML)
        player_ids = {r["player_id"] for r in rulers}
        assert 1 in player_ids
        assert 2 in player_ids
        assert 0 not in player_ids  # Should not have 0-based IDs

    def test_extract_rulers_starting_ruler_is_turn_1(self) -> None:
        """Test that starting rulers (succession_order=0) have succession_turn=1."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Find all starting rulers
        starting_rulers = [r for r in rulers if r["succession_order"] == 0]

        assert len(starting_rulers) > 0

        # All starting rulers should have succession_turn = 1
        for ruler in starting_rulers:
            assert ruler["succession_turn"] == 1, (
                f"Starting ruler {ruler['ruler_name']} should have "
                f"succession_turn=1, got {ruler['succession_turn']}"
            )

    def test_extract_rulers_archetype_format(self) -> None:
        """Test that archetypes are properly formatted."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Get archetypes (filter out None values)
        archetypes = {r["archetype"] for r in rulers if r["archetype"]}

        # Should have readable archetypes (not raw XML constants)
        valid_archetypes = {"Scholar", "Tactician", "Commander", "Schemer"}

        for archetype in archetypes:
            assert archetype in valid_archetypes, (
                f"Invalid archetype: {archetype}. "
                f"Expected one of {valid_archetypes}"
            )

            # Should not contain underscores or TRAIT_ prefix
            assert "_" not in archetype
            assert "TRAIT" not in archetype

    def test_extract_rulers_trait_format(self) -> None:
        """Test that starting traits are properly formatted."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Get starting traits (filter out None values)
        traits = {r["starting_trait"] for r in rulers if r["starting_trait"]}

        assert len(traits) > 0

        for trait in traits:
            # Should be title case
            assert trait[0].isupper(), f"Trait should be title case: {trait}"

            # Should not contain raw XML prefixes
            assert "TRAIT_" not in trait

            # Multi-word traits should have spaces
            if len(trait.split()) > 1:
                assert " " in trait

    def test_extract_rulers_ruler_name_format(self) -> None:
        """Test that ruler names are properly formatted."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Get ruler names (filter out None values)
        names = {r["ruler_name"] for r in rulers if r["ruler_name"]}

        assert len(names) > 0

        for name in names:
            # Should not contain NAME_ prefix
            assert "NAME_" not in name, f"Name should not have NAME_ prefix: {name}"

            # Should be title case
            assert name[0].isupper(), f"Name should be title case: {name}"

    def test_extract_rulers_succession_order_is_sequential(self) -> None:
        """Test that succession_order values are sequential for each player."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Group by player_id
        players = {}
        for ruler in rulers:
            player_id = ruler["player_id"]
            if player_id not in players:
                players[player_id] = []
            players[player_id].append(ruler)

        # Check each player's succession order
        for player_id, player_rulers in players.items():
            # Sort by succession_order
            player_rulers.sort(key=lambda r: r["succession_order"])

            # Verify sequential: 0, 1, 2, ...
            for i, ruler in enumerate(player_rulers):
                assert ruler["succession_order"] == i, (
                    f"Player {player_id} should have sequential succession_order. "
                    f"Expected {i}, got {ruler['succession_order']}"
                )

    def test_extract_rulers_successor_turn_greater_than_1(self) -> None:
        """Test that successor rulers (order > 0) have succession_turn > 1."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Find all successor rulers
        successors = [r for r in rulers if r["succession_order"] > 0]

        if len(successors) > 0:  # Only test if there are successors
            for ruler in successors:
                assert ruler["succession_turn"] > 1, (
                    f"Successor ruler {ruler['ruler_name']} (order "
                    f"{ruler['succession_order']}) should have succession_turn > 1, "
                    f"got {ruler['succession_turn']}"
                )

    def test_extract_rulers_with_multiple_saves(self) -> None:
        """Test extraction works across different save files."""
        import os
        from pathlib import Path

        saves_dir = Path("saves")
        save_files = list(saves_dir.glob("match_*.zip"))[:3]  # Test first 3 files

        for save_file in save_files:
            parser = OldWorldSaveParser(str(save_file))

            try:
                parser.extract_and_parse()
                rulers = parser.extract_rulers()

                # Should have at least 2 rulers (one per player minimum)
                assert len(rulers) >= 2, (
                    f"Save {save_file.name} should have at least 2 rulers"
                )

                # All rulers should have required fields
                for ruler in rulers:
                    assert ruler["player_id"] > 0
                    assert ruler["character_id"] >= 0
                    assert ruler["succession_order"] >= 0
                    assert ruler["succession_turn"] >= 1

            except Exception as e:
                pytest.fail(f"Failed to process {save_file.name}: {e}")


class TestFindSuccessionTurn:
    """Tests for the _find_succession_turn() helper method."""

    def test_find_succession_turn_basic(self) -> None:
        """Test that succession turn is found for successor rulers."""
        parser = OldWorldSaveParser("saves/match_426504721_anarkos-becked.zip")
        parser.extract_and_parse()

        rulers = parser.extract_rulers()

        # Find a successor ruler (succession_order > 0)
        successor = next(
            (r for r in rulers if r["succession_order"] > 0),
            None
        )

        if successor:
            # Should have a valid succession turn
            assert successor["succession_turn"] is not None
            assert successor["succession_turn"] > 1
