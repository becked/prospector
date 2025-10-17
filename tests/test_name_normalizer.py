"""Tests for name normalization utilities."""

from tournament_visualizer.data.name_normalizer import (
    build_name_lookup,
    find_best_match,
    names_match,
    normalize_name,
)


class TestNormalizeName:
    """Tests for normalize_name() function."""

    def test_normalize_basic(self) -> None:
        """Test basic normalization."""
        assert normalize_name("Ninja") == "ninja"

    def test_normalize_whitespace(self) -> None:
        """Test whitespace handling."""
        assert normalize_name("  Ninja  ") == "ninja"
        assert normalize_name("Fluffy Bunny") == "fluffybunny"
        assert normalize_name("Player   Name") == "playername"

    def test_normalize_special_chars(self) -> None:
        """Test special character removal."""
        assert normalize_name("Ninja [OW]") == "ninjaow"
        assert normalize_name("Player_123") == "player123"
        assert normalize_name("Test-Name!") == "testname"

    def test_normalize_unicode(self) -> None:
        """Test Unicode character handling."""
        assert normalize_name("José") == "jose"
        assert normalize_name("García") == "garcia"
        assert normalize_name("Müller") == "muller"

    def test_normalize_empty(self) -> None:
        """Test empty/None handling."""
        assert normalize_name("") == ""
        assert normalize_name(None) == ""
        assert normalize_name("   ") == ""

    def test_normalize_case(self) -> None:
        """Test case insensitivity."""
        assert normalize_name("NINJA") == "ninja"
        assert normalize_name("NiNjA") == "ninja"
        assert normalize_name("ninja") == "ninja"


class TestNamesMatch:
    """Tests for names_match() function."""

    def test_exact_match(self) -> None:
        """Test exact name matching."""
        assert names_match("Ninja", "Ninja") is True

    def test_case_insensitive(self) -> None:
        """Test case-insensitive matching."""
        assert names_match("Ninja", "ninja") is True
        assert names_match("NINJA", "ninja") is True

    def test_whitespace_match(self) -> None:
        """Test whitespace normalization."""
        assert names_match("Ninja", " Ninja ") is True
        assert names_match("Fluffy Bunny", "FluffyBunny") is True

    def test_special_char_match(self) -> None:
        """Test special character handling."""
        assert names_match("Ninja [OW]", "NinjaOW") is True
        assert names_match("Player_123", "Player123") is True

    def test_no_match(self) -> None:
        """Test non-matching names."""
        assert names_match("Ninja", "Auro") is False
        assert names_match("FluffyBunny", "Ninja") is False

    def test_empty_names(self) -> None:
        """Test empty name handling."""
        assert names_match("", "") is True
        assert names_match(None, None) is True
        assert names_match("Ninja", None) is False
        assert names_match(None, "Ninja") is False


class TestFindBestMatch:
    """Tests for find_best_match() function."""

    def test_exact_match(self) -> None:
        """Test finding exact match."""
        candidates = build_name_lookup(["Ninja", "Auro", "FluffyBunny"])

        result = find_best_match("Ninja", candidates)
        assert result == "Ninja"

    def test_case_insensitive_match(self) -> None:
        """Test case-insensitive matching."""
        candidates = build_name_lookup(["Ninja", "Auro"])

        result = find_best_match("ninja", candidates)
        assert result == "Ninja"

    def test_special_char_match(self) -> None:
        """Test matching with special characters."""
        candidates = build_name_lookup(["NinjaOW", "Auro"])

        result = find_best_match("Ninja [OW]", candidates)
        assert result == "NinjaOW"

    def test_no_match(self) -> None:
        """Test when no match exists."""
        candidates = build_name_lookup(["Ninja", "Auro"])

        result = find_best_match("Unknown", candidates)
        assert result is None

    def test_empty_candidates(self) -> None:
        """Test with empty candidate list."""
        result = find_best_match("Ninja", {})
        assert result is None


class TestBuildNameLookup:
    """Tests for build_name_lookup() function."""

    def test_basic_lookup(self) -> None:
        """Test basic lookup building."""
        names = ["Ninja", "Auro", "FluffyBunny"]
        lookup = build_name_lookup(names)

        assert lookup["ninja"] == "Ninja"
        assert lookup["auro"] == "Auro"
        assert lookup["fluffybunny"] == "FluffyBunny"

    def test_duplicate_normalized(self) -> None:
        """Test handling of names that normalize to same value."""
        names = ["Ninja", "ninja", "NINJA"]
        lookup = build_name_lookup(names)

        # Should keep first occurrence
        assert lookup["ninja"] == "Ninja"
        assert len(lookup) == 1

    def test_empty_names(self) -> None:
        """Test with empty name list."""
        lookup = build_name_lookup([])
        assert lookup == {}

    def test_ignores_empty_strings(self) -> None:
        """Test that empty strings are ignored."""
        names = ["Ninja", "", None, "Auro"]
        lookup = build_name_lookup(names)

        assert len(lookup) == 2
        assert "ninja" in lookup
        assert "auro" in lookup
