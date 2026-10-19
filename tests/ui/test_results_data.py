from __future__ import annotations

import pandas as pd
from src.ui.services.results_data import apply_display_names


def test_apply_display_names_maps_observer_and_target():
    df = pd.DataFrame(
        {
            "detecting_platform_id": ["Blue_1", "Blue_2"],
            "target_platform_id": ["Red_1", "Red_2"],
            "metric": [10, 20],
        }
    )
    name_map = {
        "Blue_1": "Hunter A",
        "Red_1": "Target X",
    }
    mapped = apply_display_names(df, name_map)
    assert mapped["detecting_platform_id"].tolist() == ["Hunter A", "Blue_2"]
    assert mapped["target_platform_id"].tolist() == ["Target X", "Red_2"]
    assert mapped["metric"].tolist() == [10, 20]


def test_apply_display_names_empty_df_or_map():
    df = pd.DataFrame()
    assert apply_display_names(df, {"Blue_1": "Hunter"}).empty

    df_data = pd.DataFrame({"detecting_platform_id": ["Blue_1"]})
    assert apply_display_names(df_data, {}).equals(df_data)
