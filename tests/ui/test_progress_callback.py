from __future__ import annotations

from unittest.mock import Mock
from src.ui.services.progress_callback import make_progress_callback


def test_make_progress_callback_updates_placeholder():
    mock_placeholder = Mock()
    callback = make_progress_callback(mock_placeholder)

    callback(1, 4)
    mock_placeholder.progress.assert_called_with(0.25, text="Replication 1 of 4")

    callback(4, 4)
    mock_placeholder.progress.assert_called_with(1.0, text="Replication 4 of 4")


def test_make_progress_callback_clamping():
    mock_placeholder = Mock()
    callback = make_progress_callback(mock_placeholder)

    # Edge cases: 0 total, or completed > total
    callback(0, 0)
    mock_placeholder.progress.assert_called_with(1.0, text="Replication 0 of 0")

    callback(6, 5)
    mock_placeholder.progress.assert_called_with(1.0, text="Replication 6 of 5")
