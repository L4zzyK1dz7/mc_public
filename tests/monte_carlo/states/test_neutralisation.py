"""Unit tests for neutralise_detected_platforms."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.monte_carlo.states.neutralisation import neutralise_detected_platforms


def _make_mock_platform(platform_id: str, team: str = "Red", neutralised: bool = False):
    platform = MagicMock()
    platform.id = platform_id
    platform.team = team
    platform.neutralised = neutralised
    return platform


def test_neutralise_marks_only_listed_ids():
    """Only platforms present in detected_ids are neutralised."""
    p1 = _make_mock_platform("Red_1", team="Red")
    p2 = _make_mock_platform("Red_2", team="Red")
    p3 = _make_mock_platform("Blue_1", team="Blue")

    newly = neutralise_detected_platforms([p1, p2, p3], {"Red_1"})

    assert newly == ["Red_1"]
    assert p1.neutralised is True
    assert p2.neutralised is False
    assert p3.neutralised is False


def test_neutralise_idempotence():
    """Calling repeatedly does not re-neutralise or re-return already neutralised platforms."""
    p1 = _make_mock_platform("Red_1")
    p2 = _make_mock_platform("Red_2")

    first_call = neutralise_detected_platforms([p1, p2], {"Red_1"})
    assert first_call == ["Red_1"]
    assert p1.neutralised is True

    # Second call with same ID
    second_call = neutralise_detected_platforms([p1, p2], {"Red_1"})
    assert second_call == []
    assert p1.neutralised is True
    assert p2.neutralised is False

    # Third call adding p2
    third_call = neutralise_detected_platforms([p1, p2], {"Red_1", "Red_2"})
    assert third_call == ["Red_2"]
    assert p2.neutralised is True


def test_neutralise_unknown_ids_ignored():
    """Unknown IDs in detected_ids are safely ignored."""
    p1 = _make_mock_platform("Blue_1", team="Blue")

    newly = neutralise_detected_platforms([p1], {"Unknown_99", "Ghost_Target"})
    assert newly == []
    assert p1.neutralised is False


def test_neutralise_both_teams():
    """Can neutralise platforms on both Blue and Red teams."""
    blue = _make_mock_platform("Blue_1", team="Blue")
    red = _make_mock_platform("Red_1", team="Red")

    newly = neutralise_detected_platforms([blue, red], {"Blue_1", "Red_1"})
    assert set(newly) == {"Blue_1", "Red_1"}
    assert blue.neutralised is True
    assert red.neutralised is True


def test_neutralise_empty_inputs():
    """Handles empty platform lists and empty detected_ids sets gracefully."""
    assert neutralise_detected_platforms([], {"Red_1"}) == []

    p1 = _make_mock_platform("Red_1")
    assert neutralise_detected_platforms([p1], set()) == []
    assert p1.neutralised is False
