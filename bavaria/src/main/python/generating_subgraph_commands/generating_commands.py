"""
Command Generator for Subgraph Creation Pipeline

This script generates shell commands to run subgraph creation for multiple cities
based on optimization parameters from a CSV file. It automates the process of
creating subgraphs with different hexagon sizes and target counts for each city.

Usage:
    python3 generating_commands.py

Output:
    Prints nohup commands that can be copied and executed to run subgraph creation
    for all cities in parallel. Each command includes city-specific parameters
    and redirects output to individual log files.

Configuration:
    Modify the global parameters at the top of the file:
    - mean_factor: Distribution mean factor (default: 4)
    - std_factor: Distribution standard deviation factor (default: 8) 
    - seed_number: Random seed for reproducibility (default: 3)
    - hexagon_sizes: List of hexagon grid sizes to process (default: [500, 1000, 2000])

Requirements:
    - City optimization data in: data/optimization_table/city_contributions.csv
    - CSV format with columns: City, contribution_500, contribution_1000, contribution_2000
"""

import pandas as pd
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent

# Global configuration parameters
mean_factor = 4
std_factor = 8
seed_number = 3
hexagon_sizes = [500, 1000, 2000]


def read_table(base_dir):
    """
    Read city optimization parameters from CSV file.
    
    Loads the optimization table containing target subgraph counts
    for each city and hexagon size combination.
    
    Args:
        base_dir (Path): Base directory containing the optimization table
        
    Returns:
        tuple: (city_names, contribution_500, contribution_1000, contribution_2000)
               - city_names: Series of city names
               - contribution_500/1000/2000: Series of target subgraph counts for each hexagon size
               
    Raises:
        FileNotFoundError: If optimization table CSV file doesn't exist
        KeyError: If required columns are missing from CSV
    """
    filename = base_dir / "data" / "optimization_table" / 'city_contributions.csv'
    dataframe = pd.read_csv(filename, delimiter=';')
    city_name = dataframe['City']
    contribution_500 = dataframe['contribution_500']
    contribution_1000 = dataframe['contribution_1000']
    contribution_2000 = dataframe['contribution_2000']
    return city_name, contribution_500, contribution_1000, contribution_2000


def generate_commands(base_dir):
    """
    Generate nohup commands for running subgraph creation on all cities.
    
    Creates complete command strings that can be executed to run the subgraph
    creation pipeline for each city with city-specific parameters. Commands
    include proper logging and background execution setup.
    
    Args:
        base_dir (Path): Base directory for resolving file paths
        
    Prints:
        Complete nohup command strings for each city, one per line.
        Each command includes:
        - City name and seed number
        - Hexagon sizes and distribution factors
        - City-specific subgraph target counts
        - Output redirection to individual log files
        
    Example Output:
        nohup python3 bavaria/src/main/python/creating_subgraphs/subgraph_creation.py augsburg 
        --seed_number 3 --hexagon_sizes 500 1000 2000 --mean_factors 4 --std_factors 8 
        --subgraph_counts 2946 3000 31 > augsburg_subgraph_creation_new.log 2>&1 &
    """
    city_name, contribution_500, contribution_1000, contribution_2000 = read_table(base_dir)
    
    for i in range(len(city_name)):
        hex_sizes_str = ' '.join(str(x) for x in hexagon_sizes)
        subgraph_counts_str = f"{contribution_500[i]} {contribution_1000[i]} {contribution_2000[i]}"
        log_file = f"{city_name[i]}_subgraph_creation_new.log"
        
        print(f"nohup python3 bavaria/src/main/python/creating_subgraphs/subgraph_creation.py {city_name[i]} "
              f"--seed_number {seed_number} --hexagon_sizes {hex_sizes_str} "
              f"--mean_factors {mean_factor} --std_factors {std_factor} "
              f"--subgraph_counts {subgraph_counts_str} > {log_file} 2>&1 &")


if __name__ == "__main__":
    generate_commands(base_dir)