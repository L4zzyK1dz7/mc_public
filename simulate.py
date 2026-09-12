"""
Command-line interface for running Monte Carlo simulations.

This script allows users to run simulations from the command line using a
pre-generated config.yaml file. It satisfies FR4.1 requirement:
"The engine shall run from the command line and be configured via a config.yaml file."

Usage:
    python simulate.py config.yaml
    python simulate.py path/to/config.yaml
    python simulate.py --help

The script will:
1. Load the configuration from the specified YAML file
2. Load random seeds from seeds.txt (if configured)
3. Execute the Monte Carlo simulation
4. Write results to data/outputs/summary_stats.csv and data/outputs/raw_positions.csv
"""
