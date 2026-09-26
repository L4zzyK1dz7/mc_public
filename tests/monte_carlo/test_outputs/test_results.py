"""Output results module tests."""

from src.monte_carlo.output.aggregate_results import aggregate_and_output_results


def test_results_module_importable():
    assert callable(aggregate_and_output_results)
