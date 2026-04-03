"""Tests for entity deduplication logic."""

import pytest
from chronicler.vault.dedup import find_match, is_duplicate


class TestFindMatch:
    def test_exact_match(self):
        existing = ["Theron", "Sylvie", "Bill Tidewater"]
        assert find_match("Theron", existing) == "Theron"

    def test_case_insensitive_match(self):
        existing = ["Theron", "Sylvie"]
        assert find_match("theron", existing) == "Theron"

    def test_alias_match(self):
        existing_with_aliases = {
            "The Friendly Face": ["the big guy", "friendly face"],
            "Sylvie": ["sylvie starwater"],
        }
        assert find_match("the big guy", [], alias_map=existing_with_aliases) == "The Friendly Face"

    def test_fuzzy_match(self):
        existing = ["Sylvie Starwater", "Bill Tidewater"]
        assert find_match("Sylvie", existing, threshold=70) == "Sylvie Starwater"

    def test_no_match(self):
        existing = ["Theron", "Sylvie"]
        assert find_match("Completely Different", existing) is None

    def test_no_false_positive(self):
        existing = ["The Black Spire", "The Farm"]
        assert find_match("The Ship", existing, threshold=80) is None


class TestIsDuplicate:
    def test_duplicate_exact(self):
        assert is_duplicate("Theron", ["Theron", "Sylvie"]) is True

    def test_not_duplicate(self):
        assert is_duplicate("New NPC", ["Theron", "Sylvie"]) is False

    def test_duplicate_with_alias(self):
        aliases = {"The Friendly Face": ["the big guy"]}
        assert is_duplicate("the big guy", ["The Friendly Face"], alias_map=aliases) is True
