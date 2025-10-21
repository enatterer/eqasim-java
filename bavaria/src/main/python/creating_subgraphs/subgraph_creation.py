"""
Subgraph Creation Pipeline for MATSim Network Analysis

This module generates subgraphs from transportation networks for feeding into MATSim simulations.
It creates spatially-aware network scenarios by reducing capacity on specific road segments 
based on centrality measures and hexagonal spatial partitioning.

Process Overview:
    1. Create hexagonal grid overlay for the city
    2. Calculate edge centrality measures (betweenness and closeness)
    3. Generate subgraphs for primary roads meeting centrality criteria
    4. Create MATSim network files with modified link capacities
    5. Save scenario data (hexagon IDs, edge geometries, network files)

Configuration:
    Modify the Control Center variables below:
    - capacity_tuning_factor: Capacity reduction factor (0.0-1.0)
    - betweenness_centrality_cutoff: Percentile cutoff for betweenness (0.0-1.0)
    - closeness_centrality_cutoff: Percentile cutoff for closeness (0.0-1.0)

Usage:
    # First, generate commands for all cities:
    python3 bavaria/src/main/python/generating_subgraph_commands/generating_commands.py
    
    # Run to create subgraphs for a specific city (explained in more detail in the generating_commands.py script):
    python3 subgraph_creation.py wuerzburg --seed_number 3 --hexagon_sizes 500 1000 2000 
            --mean_factors 4 --std_factors 8 --subgraph_counts 2946 3000 31

Input Data Structure:
data/
├── city_boundaries/
│   └── <city_name>/
│       ├── <city_name>.json
│
├── simulation_input/
│   └── simulations_per_city/
│       └── <city_name>/
│           ├── <city_name>_network.xml.gz (this is the input file from cutsimulations java class that gives the initial network file for each city and its landkreis region from the entire bavarian network)
│
├── simulation_output/
│   └── basecases/
│       └── <city_name>/
│           └── <city_name>_seed_1/
│               └── output_links.csv.gz

Output Data Structure:
data/
└── subgraph/
    ├── hexagon/
    │   └── <city_name>/
    │       └── <city_name>_seed_<number>_hex<size>_mean<mean>_std<std>/
    │           ├── plots/ # Visualization plots
    │           └── data/  # Hexagon grid and edge data
    ├── centrality/
    │   └── <city_name>/
    │       └── <city_name>_seed_<number>_hex<size>_mean<mean>_std<std>/
    │           ├── csv/
    │           └── plots/
    └── network_files/
        └── <city_name>/
            └── <city_name>_seed_<number>_hex<size>_mean<mean>_std<std>/
                ├── networks/
                └── validation/

Generated Files:
bavaria/data/subgraph/network_files/<city_name>/
This folder contains basically all the generated subgraphs for a specific city (in the networks/ subfolder).
    -   xyz_edges_of_roadtype.geojson: This file contains all edges of a specific road type (e.g., primary) that are within the hexagons of the scenario, regardless of whether their capacity was reduced or not.
    -   xyz_reduced_capacity_edges.geojson: This file contains only the edges in the scenario hexagons whose capacity was actually reduced for the scenario.
    -   xyz_hexagons.json: This file contains the list of hexagon IDs that define the scenario.
    -   xyz.xml.gz: This is the actual MATSim network file for the scenario, with modified capacities.

bavaria/data/subgraph/hexagon/<city_name>/
This folder contains the hexagon grids for each city and all the edges that fall within the hexagons and related plots for a specific city.(in the data/ and plots/ subfolders).

Notes:
    - Uses EPSG:25832 coordinate system (adjust for other regions)
    - Currently optimized for primary roads only
    - Supports parallel processing for scenario generation
"""

# Add the current directory to Python path
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Standard library imports
import gzip
import logging
import multiprocessing as mp
from collections import Counter
from functools import reduce
from itertools import islice
from pathlib import Path
import random
import sys
import re
import json
import argparse

# Third-party imports
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely import wkt
from shapely.geometry import LineString, box, Polygon
import shapely.geometry as sgeo
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.colors import Normalize
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
from typing import Dict, List, Tuple, Set, Optional
import shutil
import time
from datetime import datetime

# Local imports
import network_io as nio
from hexagon_creation_and_plot import *
from betweenness_and_closeness import *

### Settings for filepath, working directory and output path #########################################################
base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent

######## Control Center for Variables #################################################################################
capacity_tuning_factor = 0.5 #This is the factor by which the capacity of the links is reduced
betweenness_centrality_cutoff = 0.8 # Take the lowest 80% of the links based on betweenness centrality
closeness_centrality_cutoff = 0.2 # Take the highest 80% of the links based on closeness centrality
########################################################################################################################

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='Create subgraphs for a given city.')
    parser.add_argument('city', type=str, help='Name of the city (e.g., augsburg, ingolstadt)')
    parser.add_argument('--seed_number', type=int, help='Seed number for the random number generator')
    parser.add_argument('--hexagon_sizes', type=int, nargs='+', required=True)
    parser.add_argument('--mean_factors', type=int, help='Distribution mean factor')
    parser.add_argument('--std_factors', type=int, help='Distribution std factor')
    parser.add_argument('--subgraph_counts', type=int, nargs='+', required=True)
    
    return parser.parse_args()

def setup_output_directories(base_dir, city_name, seed_number, hexagon_size, mean_factor, std_factor):
    """
    Create structured output directories for subgraph generation.
    
    Args:
        base_dir (Path): Base directory path
        city_name (str): Name of the city (e.g., 'augsburg')
        seed_number (int): Random seed number
        hexagon_size (int): Size of hexagon grid cells
        mean_factor (int): Distribution mean factor
        std_factor (int): Distribution standard deviation factor
    
    Returns:
        dict: Dictionary containing paths for all output directories:
              - hexagon_plots, hexagon_data: Hexagon grid files
              - centrality_csv, centrality_plots: Centrality analysis files  
              - network_files, networks, validation: Network scenario files
    """
    city_seed_dir = f"{city_name}_seed_{seed_number}_hex{hexagon_size}_mean{mean_factor}_std{std_factor}"
    output_base_path = base_dir / "data" / "subgraph"
    output_paths = {
        'hexagon': output_base_path / "hexagon" / city_name / city_seed_dir,
        'centrality': output_base_path / "centrality" / city_name / city_seed_dir,
        'network_files': output_base_path / "network_files" / city_name / city_seed_dir,
        'networks': output_base_path / "network_files" / city_name / city_seed_dir / "networks",
        'validation': output_base_path / "network_files" / city_name / city_seed_dir / "validation"
    }
    
    # Create all directories and their subdirectories
    for path in output_paths.values():
        path.mkdir(parents=True, exist_ok=True)
        
        if 'hexagon' in str(path):
            (path / "plots").mkdir(exist_ok=True)
            (path / "data").mkdir(exist_ok=True)
        elif 'centrality' in str(path):
            (path / "csv").mkdir(exist_ok=True)
            (path / "plots").mkdir(exist_ok=True)
    
    # Return complete path dictionary
    return {
        'base': output_base_path,
        'hexagon_plots': output_paths['hexagon'] / "plots",
        'hexagon_data': output_paths['hexagon'] / "data",
        'centrality_csv': output_paths['centrality'] / "csv",
        'centrality_plots': output_paths['centrality'] / "plots",
        'network_files': output_paths['network_files'],
        'networks': output_paths['networks'],
        'validation': output_paths['validation']
    }

def generate_road_type_specific_subsets(gdf_edges_with_hex, city_name, seed_number, target_size, 
                                       hexagon_size, distribution_mean_factor, distribution_std_factor,
                                       betweenness_centrality_cutoff=betweenness_centrality_cutoff,
                                       closeness_centrality_cutoff=closeness_centrality_cutoff):
    """
    Generate unique hexagon ID subsets for each road type based on centrality criteria.
    
    Filters edges by centrality thresholds and creates random subsets of hexagons 
    containing the target road types for scenario generation.
    
    Args:
        gdf_edges_with_hex (GeoDataFrame): Network edges with hexagon assignments
        city_name (str): Name of the city
        seed_number (int): Random seed for reproducibility
        target_size (int): Total number of subsets (subgraphs) to generate
        hexagon_size (int): Size of hexagon grid cells
        distribution_mean_factor (int): Factor for subset size mean calculation
        distribution_std_factor (int): Factor for subset size std deviation
        betweenness_centrality_cutoff (float, optional): Percentile cutoff for betweenness
        closeness_centrality_cutoff (float, optional): Percentile cutoff for closeness
    
    Returns:
        tuple: (road_type_subsets, target_mean, overall_mean, subset_count)
               - road_type_subsets: Dict mapping road types to hexagon ID lists, for our use case only for primary roads, example: {'primary': [(hex1, hex2, ...), (hex3, hex4, ...), ...]}
               - target_mean: Target mean subset size
               - overall_mean: Actual mean subset size
               - subset_count: Number of subsets generated
    """
    # Set the seed for reproducibility using the seed_number from directory structure
    np.random.seed(seed_number)
    random.seed(seed_number)
    gdf_filtered = gdf_edges_with_hex[gdf_edges_with_hex['is_in_stadt'] == 1].copy()
    closeness_cutoff = gdf_filtered['closeness'].quantile(closeness_centrality_cutoff)
    betweenness_cutoff = gdf_filtered['betweenness'].quantile(betweenness_centrality_cutoff)
    print(f"Betweenness centrality cutoff (80th percentile): {betweenness_cutoff}")
    print(f"Closeness centrality cutoff (80th percentile): {closeness_cutoff}")
    
    # Analyze hexagons per road type for edges meeting centrality criteria
    print("\nAnalyzing hexagons per road type for edges meeting centrality criteria:")
    centrality_mask =((gdf_filtered['betweenness'] < betweenness_cutoff) & 
                      (gdf_filtered['closeness'] > closeness_cutoff))
    edges_meeting_criteria = gdf_filtered[centrality_mask]
    
    # Create a dictionary to store hexagon counts per road type
    hexagons_per_road_type = {}
    
    target_road_types = ['primary']
    road_types = [rt for rt in target_road_types if rt in edges_meeting_criteria['consolidated_road_type'].unique()]
    
    # First, collect all hexagons for each road type
    road_type_hexagons = {}
    for road_type in road_types:
        # 1. Find all edges of this road type
        roadtype_mask = edges_meeting_criteria['consolidated_road_type'] == road_type
        edges_of_type = edges_meeting_criteria[roadtype_mask]

        # 2. Collect all unique hexagons for this road type
        possible_hex_ids = set()
        for hex_list in edges_of_type['hexagon']:
            if isinstance(hex_list, list):
                possible_hex_ids.update(hex_list)
        possible_hex_ids = sorted(list(possible_hex_ids))
        n_hex = len(possible_hex_ids)
        
        # Store the hexagons for this road type
        road_type_hexagons[road_type] = possible_hex_ids
        
        # Store the count
        hexagons_per_road_type[road_type] = n_hex
        
        # Print summary in your desired format
        print(f"Road type: {road_type}")
        print(f"Number of edges meeting criteria: {len(edges_of_type)}")
        print(f"Number of unique hexagons: {n_hex}")
        print(f"Unique hexagons: {set(possible_hex_ids)}")
        print("-" * 50)
    
    print(f"\nGenerating subsets for {city_name} with seed {seed_number}")
    
    # Dictionary to store subsets for each road type
    road_type_subsets = {}
    
    for road_type in road_types:
        print(f"Generating subsets for road type: {road_type}")
        # Get hexagons that contain this road type
        road_type_hexagons_list = road_type_hexagons[road_type]
        if not road_type_hexagons_list:
            print(f"Warning: No hexagons found for road type {road_type}")
            continue
        n_hex = len(road_type_hexagons_list)

        # 2. Subset generation parameters
        target_mean = n_hex / distribution_mean_factor
        std_dev = n_hex / distribution_std_factor
        subsets_per_type = target_size // len(road_types)
        # 3. Generate subsets
        unique_subsets = set()
        attempts = 0
        max_attempts = 10*subsets_per_type
        while len(unique_subsets) < subsets_per_type:
            subset_size = max(1, round(np.random.normal(target_mean, std_dev)))
            subset_size = min(subset_size, n_hex)
            subset = tuple(sorted(random.sample(possible_hex_ids, subset_size)))
            unique_subsets.add(subset)
            attempts += 1
            if attempts > max_attempts:
                print(f"Warning: Could not generate {subsets_per_type} unique subsets for {road_type} after {max_attempts} attempts")
                break
        if len(unique_subsets) < subsets_per_type:
            print(f"Warning: Could not generate {subsets_per_type} unique subsets for {road_type} after {max_attempts} attempts")
        # 4. Store
        road_type_subsets[road_type] = list(unique_subsets)
        subset_count = len(road_type_subsets[road_type])
        print(f"Generated {subset_count} subsets for {road_type}")
    
        # Calculate overall statistics
        all_subsets = [subset for subsets in road_type_subsets.values() for subset in subsets]
        overall_mean = np.mean([len(s) for s in all_subsets])
        
        print(f"\nSubset Generation Summary for {city_name}:")
        print(f"Total number of unique hexagons: {n_hex}")
        print(f"Target mean based on unique hexagons: {target_mean:.2f}")
        print(f"Target std dev based on unique hexagons: {std_dev:.2f}")
        print(f"Overall actual mean subset length for hexagon size {hexagon_size}: {overall_mean:.2f}")
        print(f"Number of road types: {len(road_types)}")
        print(f"Subgraph count: {subsets_per_type}")
        print(f"Total number of subsets generated for hexagon size {hexagon_size}: {subset_count}")
        print(f"City: {city_name}")
        print(f"Seed number: {seed_number}")
        return road_type_subsets, target_mean, overall_mean, subset_count

def generate_scenario_labels(road_type_subsets, city_name):
    """
    Generate meaningful labels for scenario combinations.
    
    Args:
        road_type_subsets (dict): Dictionary mapping road types to hexagon subsets, example: {'primary': [(hex1, hex2, ...), (hex3, hex4, ...), ...]}
        city_name (str): Name of the city
    
    Returns:
        dict: Dictionary mapping scenario indices (road_type, subset_index) to 
              descriptive labels in format: "{city}_{road_type}_n{hex_count}_s{scenario_num}"
    Example scenario
    """
    # Get all road types
    road_types = list(road_type_subsets.keys())
    
    # Create a mapping for scenario labels
    scenario_labels = {}
    
    # For each road type
    for road_type in road_types:
        # For each subset in this road type
        for i, subset in enumerate(road_type_subsets[road_type]):
            # Create a label that includes:
            # 1. City name  
            # 2. Road type
            # 3. Number of hexagons in the subset
            # 4. Scenario number
            label = f"{city_name}_{road_type}_n{len(subset)}_s{i+1}"
            scenario_labels[(road_type, i)] = label
    
    return scenario_labels

def process_one_scenario(args):
    (road_type, subset, i, gdf_filtered, scenario_labels, city_name, seed_number,
        networks_base, matsim_network_file_path, capacity_tuning_factor, label,
        betweenness_cutoff, closeness_cutoff
    ) = args
    """
    Process a single scenario by creating network files with modified capacities.
    
    This function is designed for parallel execution and handles:
    - Filtering edges by road type, centrality criteria, and transport modes
    - Selecting edges in scenario hexagons that meet all criteria
    - Saving hexagon IDs and edge geometries  
    - Modifying link capacities in MATSim network XML
    
    Edge filtering criteria:
    - Road type must match scenario road type
    - Betweenness centrality below specified cutoff (lowest X%)
    - Closeness centrality above specified cutoff (highest X%)
    - Must allow car or car_passenger modes
    
    Args:
        args (tuple): Contains all parameters needed for scenario processing:
                     (road_type, subset, scenario_index, filtered_gdf, scenario_labels,
                      city_name, seed_number, networks_base, matsim_network_file_path,
                      capacity_tuning_factor, label, betweenness_cutoff, closeness_cutoff)
    
    Returns:
        str: Path to the created network file (for validation and checking)
    """
    (road_type, subset, i, gdf_filtered, scenario_labels, city_name, seed_number,
        networks_base, matsim_network_file_path, capacity_tuning_factor, label,
        betweenness_cutoff, closeness_cutoff
    ) = args
    print(f"Processing scenario {label}",flush=False)
    import gzip, json, re
    import pandas as pd
    # Select edges for this road type and scenario (centrality, mode, road type)
    road_type_mask = (
        (gdf_filtered['consolidated_road_type'] == road_type) &
        (gdf_filtered['betweenness'] < betweenness_cutoff) &
        (gdf_filtered['closeness'] > closeness_cutoff) &
        (gdf_filtered['modes'].apply(lambda x: any(mode in ['car', 'car_passenger'] for mode in str(x).split(','))))
    )
    road_type_edges = gdf_filtered[road_type_mask].copy()
    # Get edges in scenario hexagons for this road type, that are in the subset and meet the conditions
    scenario_mask = road_type_edges['hexagon'].apply(
        lambda x: any(h in subset for h in x) if isinstance(x, list) else False
    )
    scenario_edges = road_type_edges[scenario_mask].copy()
    scenario_edges['scenario_hexagons'] = str(list(subset))
    # Save hexagon IDs for this scenario
    hexagon_data = {
        "scenario": label,
        "road_type": road_type,
        "seed": seed_number,
        "hexagon_ids": list(subset)
    }
    hexagon_filename = f"network_seed{seed_number}_{label}_hexagons.json"
    hexagon_path = networks_base / hexagon_filename
    with open(hexagon_path, 'w') as f:
        json.dump(hexagon_data, f, indent=2)
    # Save the scenario edges (reduced capacity)
    scenario_edges_filename = f"network_seed{seed_number}_{label}_reduced_capacity_edges.geojson"
    scenario_edges_path = networks_base / scenario_edges_filename
    scenario_edges_to_save = scenario_edges.copy()
    for column in scenario_edges_to_save.columns:
        if isinstance(scenario_edges_to_save[column].iloc[0], list):
            scenario_edges_to_save[column] = scenario_edges_to_save[column].apply(lambda x: str(x) if isinstance(x, list) else x)
    scenario_edges_to_save.to_file(scenario_edges_path, driver='GeoJSON')
    # Save all edges of the road type in the hexagon subset (regardless of capacity reduction)
    edges_of_roadtype_mask = (
        (gdf_filtered['consolidated_road_type'] == road_type) &
        (gdf_filtered['hexagon'].apply(lambda x: any(h in subset for h in x) if isinstance(x, list) else False))
    )
    edges_of_roadtype = gdf_filtered[edges_of_roadtype_mask].copy()
    edges_of_roadtype_filename = f"network_seed{seed_number}_{label}_edges_of_roadtype.geojson"
    edges_of_roadtype_path = networks_base / edges_of_roadtype_filename
    for column in edges_of_roadtype.columns:
        if isinstance(edges_of_roadtype[column].iloc[0], list):
            edges_of_roadtype[column] = edges_of_roadtype[column].apply(lambda x: str(x) if isinstance(x, list) else x)
    edges_of_roadtype.to_file(edges_of_roadtype_path, driver='GeoJSON')
    # Read the original network file
    with gzip.open(matsim_network_file_path, 'rt', encoding='utf-8') as f:
        xml_str = f.read()
    # Create a set of tuples (link_id, from_node, to_node) that need capacity reduction
    links_to_modify = set(zip(scenario_edges['link'].values, 
                             scenario_edges['from_node'].values, 
                             scenario_edges['to_node'].values))
    # Modify only the capacity of the specified links
    for link_id, from_node, to_node in links_to_modify:
        pattern = (
            rf'(<link[^>]*\bid="{link_id}"[^>]*\bfrom="{from_node}"[^>]*\bto="{to_node}"[^>]*capacity=")([^"]+)(")'
        )
        def replace_capacity(match):
            original = float(match.group(2))
            new_capacity = original * capacity_tuning_factor
            print(f"  Modifying link {link_id}: {original} -> {new_capacity}")
            return f'{match.group(1)}{new_capacity}{match.group(3)}'
        
        # Count matches and apply replacement
        matches_before = len(re.findall(pattern, xml_str))
        xml_str = re.sub(pattern, replace_capacity, xml_str)
        
        if matches_before == 0:
            print(f"  WARNING: No matches found for link {link_id}")
        elif matches_before > 1:
            print(f"  WARNING: Multiple matches ({matches_before}) found for link {link_id}")
    
    print(f"✅ Processed {len(links_to_modify)} links for capacity modification in scenario {label}")
    # Write the modified XML to a new gzipped file
    network_filename = f"network_seed{seed_number}_{label}.xml.gz"
    network_path = networks_base / network_filename
    with gzip.open(network_path, 'wt', encoding='utf-8') as f:
        f.write(xml_str)
    return str(network_path)

def create_scenario_networks(matsim_network_file_path, gdf_edges_with_hex, road_type_subsets, 
                            scenario_labels, hexagon_size, city_name, seed_number, output_dirs, 
                            nodes_dict, network_attrs, link_attrs, capacity_tuning_factor=capacity_tuning_factor,
                            betweenness_centrality_cutoff=betweenness_centrality_cutoff,
                            closeness_centrality_cutoff=closeness_centrality_cutoff):
    """
    Create MATSim network files for all scenarios with modified link capacities.
    
    Uses parallel processing to generate network.xml.gz files where specific links
    have reduced capacity based on road type and hexagon selection criteria.
    
    Args:
        matsim_network_file_path (Path): Path to original MATSim network file
        gdf_edges_with_hex (GeoDataFrame): Network edges with hexagon assignments
        road_type_subsets (dict): Road type to hexagon subset mappings
        scenario_labels (dict): Scenario index to label mappings
        hexagon_size (int): Size of hexagon grid cells
        city_name (str): Name of the city
        seed_number (int): Random seed number
        output_dirs (dict): Output directory paths
        nodes_dict (dict): Node ID to coordinate mappings
        network_attrs (dict): Network-level attributes
        link_attrs (dict): Link-level attributes
        capacity_tuning_factor (float, optional): Factor for capacity reduction
        betweenness_centrality_cutoff (float, optional): Betweenness percentile cutoff
        closeness_centrality_cutoff (float, optional): Closeness percentile cutoff
    
    Returns:
        str: Path to the first created scenario network file (for validation and checking)
    """
    networks_base = output_dirs['networks']
    print(f"\nCreating scenario networks for {city_name} (seed {seed_number})")
    print(f"Output directory: {networks_base}")
    gdf_filtered = gdf_edges_with_hex[gdf_edges_with_hex['is_in_stadt'] == 1].copy()
    closeness_cutoff = gdf_filtered['closeness'].quantile(closeness_centrality_cutoff)
    betweenness_cutoff = gdf_filtered['betweenness'].quantile(betweenness_centrality_cutoff)
    print(f"Betweenness centrality cutoff (80th percentile): {betweenness_cutoff}")
    print(f"Closeness centrality cutoff (80th percentile): {closeness_cutoff}")
    tasks = []
    for road_type, subsets in road_type_subsets.items():
        for i, subset in enumerate(subsets):
            label = scenario_labels[(road_type, i)]
            tasks.append((
                road_type, subset, i, gdf_filtered, scenario_labels, city_name, seed_number,
                networks_base, matsim_network_file_path, capacity_tuning_factor, label,
                betweenness_cutoff, closeness_cutoff
            ))
    first_scenario_path = None
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(process_one_scenario, task) for task in tasks]
        for idx, f in enumerate(tqdm(as_completed(futures), total=len(futures), desc="Creating subgraphs")):
            result = f.result()
            if idx == 0:
                first_scenario_path = result
    print(f"\nFinished creating {len(tasks)} network files and hexagon files for {city_name} (seed {seed_number})")
    print(f"Files are organized in folders under: {networks_base}")
    return first_scenario_path

def plot_check_for_created_networks(check_output_subgraph_path, zones_gdf, hexagon_grid_all, 
                                   gdf_edges_with_hex, scenario_labels, road_type_subsets, output_dirs=None):
    """
    Visualize and validate a created network scenario.
    
    Creates a plot showing the scenario's hexagons, affected edges, and road types
    to verify that network creation worked correctly.
    
    Args:
        check_output_subgraph_path (Path): Path to network file to validate
        zones_gdf (GeoDataFrame): Zone boundaries
        hexagon_grid_all (GeoDataFrame): All hexagons in the grid
        gdf_edges_with_hex (GeoDataFrame): Original network with hexagon assignments
        scenario_labels (dict): Scenario index to label mappings
        road_type_subsets (dict): Road type to hexagon subset mappings
        output_dirs (dict, optional): Output directories for saving plots
    
    Returns:
        GeoDataFrame: The loaded MATSim network for further analysis
    """
    # Load the network file
    matsim_network, nodes_subgraph, edges_subgraph,network_attrs, link_attrs = matsim_network_input_to_gdf(check_output_subgraph_path)
    
    # Match the highway_consolidated column from gdf_edges_with_hex to matsim_network
    highway_mapping = dict(zip(gdf_edges_with_hex['link'], gdf_edges_with_hex['consolidated_road_type']))
    matsim_network['consolidated_road_type'] = matsim_network['id'].map(highway_mapping)
    
    fig, ax = plt.subplots(figsize=(15, 15))
    
    # Plot the districts
    zones_gdf.plot(ax=ax, 
                      column='zone_id',
                      cmap='YlGnBu',
                      alpha=0.3,
                      legend=False,
                      legend_kwds={'label': 'District Area (m²)'},
                      label='Districts')
    
    # Plot hexagons
    hexagon_grid_all.plot(ax=ax, color='none', edgecolor='green', alpha=0.3, label='Hexagons')
    
    # Get scenario label from filename (handling both old and new filename formats)
    filename = Path(check_output_subgraph_path).name
    if 'seed' in filename:
        # New format: network_seedX_label.xml.gz
        scenario_label = filename.split('_', 2)[2].split('.xml.gz')[0]
    else:
        # Old format: network_label.xml.gz
        scenario_label = filename.replace('network_', '').split('.xml.gz')[0]
    
    key = next((k for k, v in scenario_labels.items() if v == scenario_label), None)
    if key is None:
        print(f"Warning: Could not find matching scenario label for {scenario_label}")
        return matsim_network
        
    hex_ids = road_type_subsets[key[0]][key[1]]
    
    # Create mask for scenario edges
    scenario_mask = gdf_edges_with_hex['hexagon'].apply(
        lambda x: any(h in hex_ids for h in x) if isinstance(x, list) else False
    )
    
    # Plot parent network edges (not in scenario)
    parent_edges = matsim_network[~matsim_network['id'].isin(gdf_edges_with_hex[scenario_mask]['link'])]
    parent_edges.plot(ax=ax, 
                     color='gray',
                     linewidth=0.5,
                     alpha=0.5,
                     label='Parent Network')
    
    # Plot all scenario edges
    scenario_edges = matsim_network[matsim_network['id'].isin(gdf_edges_with_hex[scenario_mask]['link'])]
    scenario_edges.plot(ax=ax, 
                       color='red',
                       linewidth=0.5,
                       alpha=0.8,
                       label='Scenario Edges')
    
    # Plot scenario edges that match the road type from scenario label
    road_type = key[0]  # Get the road type from the key
    matching_edges = scenario_edges[scenario_edges['consolidated_road_type'] == road_type]
    matching_edges.plot(ax=ax,
                       color='blue',
                       linewidth=0.5,
                       alpha=0.8,
                       label=f'Road Type: {road_type}')
    
    legend_elements = [
        Patch(facecolor='none', edgecolor='green', alpha=0.3, label='Hexagons'),
        Line2D([0], [0], color='gray', linewidth=0.5, alpha=0.5, label='Parent Network'),
        Line2D([0], [0], color='red', linewidth=0.5, alpha=0.8, label='Scenario Edges'),
        Line2D([0], [0], color='blue', linewidth=2, alpha=0.8, label=f'Road Type: {road_type}')
    ]

    ax.legend(handles=legend_elements)
    plt.title(f'MATSim Network with Scenario Edges\n{scenario_label}')
    plt.axis('equal')
    
    # Save the plot if output_dirs is provided
    if output_dirs is not None:
        plot_path = output_dirs['validation'] / f'network_check_{scenario_label}.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"Validation plot saved to: {plot_path}")
    else:
        plt.show()
    
    plt.close()
    
    # Print some validation statistics
    print(f"\nValidation Statistics for {scenario_label}:")
    print(f"Total edges in network: {len(matsim_network)}")
    print(f"Edges in scenario hexagons: {len(scenario_edges)}")
    print(f"Edges matching road type '{road_type}': {len(matching_edges)}")
    print(f"Number of hexagons in subset: {len(hex_ids)}")
    
    return matsim_network

def cross_check_for_created_networks(check_output_subgraph_path, gdf_edges_with_hex, road_type_subsets, 
                                    scenario_labels, seed_number=None, output_dirs=None):
    """
    Cross-validate created network files by analyzing edge selection and capacity changes.
    
    Verifies which edges are in selected hexagons, match road types, and have
    modified capacities as expected.
    
    Args:
        check_output_subgraph_path (Path): Path to network file to validate
        gdf_edges_with_hex (GeoDataFrame): Original network with hexagon assignments
        road_type_subsets (dict): Road type to hexagon subset mappings
        scenario_labels (dict): Scenario index to label mappings
        seed_number (int, optional): Random seed number for reporting
        output_dirs (dict, optional): Output directories for saving validation files
    
    Returns:
        tuple: (edges_with_matching_road_type, all_edges_in_hexagons, capacity_comparison_df)
               - edges_with_matching_road_type: Edges matching scenario road type
               - all_edges_in_hexagons: All edges in scenario hexagons
               - capacity_comparison_df: DataFrame comparing original vs modified capacities
    """
    # Load the network file
    matsim_network, nodes_subgraph, edges_subgraph,network_attrs, link_attrs = matsim_network_input_to_gdf(check_output_subgraph_path)
    
    # Get scenario information (handling both old and new filename formats)
    filename = Path(check_output_subgraph_path).name
    if 'seed' in filename:
        # New format: network_seedX_label.xml.gz
        scenario_label = filename.split('_', 2)[2].split('.xml.gz')[0]
    else:
        # Old format: network_label.xml.gz
        scenario_label = filename.replace('network_', '').split('.xml.gz')[0]
    
    key = next((k for k, v in scenario_labels.items() if v == scenario_label), None)
    if key is None:
        print(f"Warning: Could not find matching scenario label for {scenario_label}")
        return None, None, None
        
    hex_ids = road_type_subsets[key[0]][key[1]]
    
    # Get edges in selected hexagons
    mask = gdf_edges_with_hex['hexagon'].apply(
        lambda x: any(hex_id in x for hex_id in hex_ids) if isinstance(x, list) else False
    )
    edges_in_selected_hexagon = gdf_edges_with_hex[mask]
    
    # Get edges that match both hexagon and road type
    edges_in_selected_hexagon_and_road_type = edges_in_selected_hexagon[
        edges_in_selected_hexagon['consolidated_road_type'] == key[0]
    ]
    
    # Create a comparison DataFrame for the capacity changes
    comparison_df = pd.DataFrame({
        'edge_id': edges_in_selected_hexagon['link'],
        'road_type': edges_in_selected_hexagon['consolidated_road_type'],
        'original_capacity': pd.to_numeric(edges_in_selected_hexagon['capacity'], errors='coerce'),
        'modified_capacity': edges_in_selected_hexagon['link'].map(
            lambda x: float(matsim_network.loc[matsim_network['id'] == x, 'capacity'].iloc[0]) 
            if x in matsim_network['id'].values else None
        )
    })
    
    # Calculate capacity_reduced based on actual capacity changes
    comparison_df['road_type_match'] = (comparison_df['road_type'] == key[0])
    comparison_df['is_capacity_reduced'] = (comparison_df['road_type_match']) & (comparison_df['modified_capacity'] < comparison_df['original_capacity'])

    # Remove rows where modified_capacity is None (edges that don't exist in the modified network)
    comparison_df = comparison_df.dropna(subset=['modified_capacity'])
    
    # Print summary statistics
    print(f"\nCross-check Summary for {scenario_label}:")
    print(f"Total edges in selected hexagons: {len(edges_in_selected_hexagon)}")
    print(f"Edges matching road type '{key[0]}': {len(edges_in_selected_hexagon_and_road_type)}")
    print(f"Number of hexagons in subset: {len(hex_ids)}")
    if seed_number is not None:
        print(f"Seed number: {seed_number}")
    
    # Save DataFrames as CSV if output_dirs is provided
    if output_dirs is not None:
        validation_dir = output_dirs['validation']
        
        # Save edges with matching road type
        road_type_file = validation_dir / f'{scenario_label}_matching_road_type.csv'
        edges_in_selected_hexagon_and_road_type.to_csv(road_type_file, index=False)
        print(f"Saved matching road type edges to: {road_type_file}")
        
        # Save all edges in selected hexagons
        hexagon_file = validation_dir / f'{scenario_label}_all_hexagon_edges.csv'
        edges_in_selected_hexagon.to_csv(hexagon_file, index=False)
        print(f"Saved hexagon edges to: {hexagon_file}")
        
        # Save capacity comparison
        capacity_file = validation_dir / f'{scenario_label}_capacity_changes.csv'
        comparison_df.to_csv(capacity_file, index=False)
        print(f"Saved capacity changes to: {capacity_file}")
    
    return edges_in_selected_hexagon_and_road_type, edges_in_selected_hexagon, comparison_df

def weighted_mean(target_mean_list, actual_mean_list, subgraph_count_list):
    """
    Calculate weighted means of target and actual subset sizes across all hexagon sizes.
    
    Args:
        target_mean_list (list): Target mean sizes for each hexagon size
        actual_mean_list (list): Actual mean sizes for each hexagon size  
        subgraph_count_list (list): Number of subgraphs for each hexagon size
    
    Prints:
        Target and actual weighted means across all scenarios
    """
    total_subgraph_count = sum(subgraph_count_list)
    target_weighted_mean = sum(np.array(target_mean_list) * np.array(subgraph_count_list)) / total_subgraph_count
    actual_weighted_mean = sum(np.array(actual_mean_list) * np.array(subgraph_count_list)) / total_subgraph_count
    print(f"Target weighted mean of the length of the subgraphs: {target_weighted_mean}")
    print(f"Actual weighted mean of the length of the subgraphs: {actual_weighted_mean}")

def main():
    """
    Main execution function for subgraph creation pipeline.
    
    Orchestrates the complete workflow:
    1. Parse command line arguments
    2. Load and process network data
    3. Create hexagon grids
    4. Calculate centrality measures
    5. Generate road type specific subsets
    6. Create scenario networks with modified capacities
    7. Validate created networks
    8. Calculate weighted statistics across all scenarios
    
    Processes multiple hexagon sizes and subgraph counts as specified in arguments.
    """
    # Parse command line arguments
    args = parse_arguments()
    city_name = args.city.lower()  # Convert to lowercase for consistency
    distribution_mean_factor = args.mean_factors
    distribution_std_factor = args.std_factors
    seed_number = args.seed_number
    base_dir = Path(__file__).parent.parent.parent.parent.parent
    
    target_mean_list = []
    actual_mean_list = []
    subgraph_count_list = []
    
    for hex_size, subgraph_count in zip(args.hexagon_sizes, args.subgraph_counts):
        print('Running for hexagon size: ', hex_size, 'and subgraph count: ', subgraph_count, 'mean factor: ', args.mean_factors, 'std factor: ', args.std_factors)
        hexagon_size = hex_size
        target_size = subgraph_count
        output_dirs = setup_output_directories(base_dir, city_name, seed_number, hex_size, args.mean_factors, args.std_factors)
        
        #### Hexagon Creation ################################################################################
        # Update file paths with the city name
        administrative_boundary_json_path = base_dir / "data" / "city_boundaries" / city_name / f"{city_name}.json"
        matsim_network_file_path = base_dir / "data" / "simulation_input" / "simulation_per_city" / city_name / f"{city_name}_network.xml.gz"
        csv_filepath = base_dir / "data" / "simulation_output" / "basecases_new" / city_name / f"{city_name}_seed_1" / "output_links.csv.gz"

        # Check if required files exist
        if not administrative_boundary_json_path.exists():
            raise FileNotFoundError(f"City boundary file not found: {administrative_boundary_json_path}")
        if not matsim_network_file_path.exists():
            raise FileNotFoundError(f"MATSim network file not found: {matsim_network_file_path}")
        if not csv_filepath.exists():
            raise FileNotFoundError(f"CSV output file not found: {csv_filepath}")

        matsim_network, nodes, df_edges, network_attrs, link_attrs = matsim_network_input_to_gdf(matsim_network_file_path)
        cleaned_network = clean_duplicates_based_on_modes(csv_filepath)
        cleaned_network['geometry'] = cleaned_network['geometry'].apply(wkt.loads) 
        # Create GeoDataFrame with all attributes
        cleaned_network = gpd.GeoDataFrame(cleaned_network, geometry='geometry', crs='EPSG:25832')
        nodes_dict = create_nodes_dict(cleaned_network)
        
        gdf = gpd.read_file(administrative_boundary_json_path)
        #modify the zones geodataframe
        zones_gdf = modify_geodataframe(gdf)
        #merge the edges with the zones
        gdf_edges_with_zones = merge_edges_and_zones(cleaned_network, zones_gdf)
        #generate the hexagon grid for the polygon
        gdf_edges_with_hex,hexagon_grid_all = merge_edges_and_hexagon_grid(zones_gdf, hexagon_size ,
                                                                          gdf_edges_with_zones ,
                                                                                  projection='EPSG:25832')
        # Prepare hexagon grid for saving
        hexagon_grid_save = hexagon_grid_all.copy()
        # Convert list fields to strings
        for col in hexagon_grid_save.columns:
            if hexagon_grid_save[col].dtype == object and isinstance(hexagon_grid_save[col].iloc[0], list):
                hexagon_grid_save[col] = hexagon_grid_save[col].apply(lambda x: str(x) if isinstance(x, list) else x)
        
        # Save the processed hexagon grid
        hexagon_grid_save.to_file(output_dirs['hexagon_data'] / f'{city_name}_hexagon_grid.geojson', driver='GeoJSON')
        #consolidate the road types
        gdf_edges_with_hex['consolidated_road_type'] = gdf_edges_with_hex['osm:way:highway'].apply(consolidate_road_types)
        #check the hexagon statistics
        check_hexagon_statistics(gdf_edges_with_hex, hexagon_grid_all)
        #plot the grid and the edges
        plot_grid_and_edges(gdf_edges_with_hex, hexagon_grid_all,zones_gdf,output_dirs,city_name)
        # Save the GeoDataFrame using the new function
        #convert_and_save_geodataframe(gdf_edges_with_hex, output_dirs['hexagon_data'] / f'{city_name}_hexagon_edges.geojson')
        
       #calculate the betweenness and closeness centrality####################################################
        
        centrality_df, gdf_edges_with_hex, G = analyze_centrality_measures(gdf_edges_with_hex, output_dirs, city_only=True)
        size_counts, largest_component= verify_components(G) 
           
        #### Subgraph Creation ###############################################################################
        
        #generate the road type specific subsets
        road_type_subsets, target_mean, overall_mean, subset_count = generate_road_type_specific_subsets(gdf_edges_with_hex, city_name,
                                                                distribution_mean_factor=distribution_mean_factor, 
                                                                distribution_std_factor=distribution_std_factor,
                                                                betweenness_centrality_cutoff=betweenness_centrality_cutoff,
                                                                closeness_centrality_cutoff=closeness_centrality_cutoff,
                                                                seed_number=seed_number,
                                                                target_size=target_size,
                                                                hexagon_size=hexagon_size)
        target_mean_list.append(target_mean)
        actual_mean_list.append(overall_mean)
        subgraph_count_list.append(subset_count)
        #generate the scenario labels
        scenario_labels = generate_scenario_labels(road_type_subsets, city_name)
        #create the scenario networks and get the first scenario path
        first_scenario = create_scenario_networks(matsim_network_file_path, gdf_edges_with_hex, road_type_subsets, scenario_labels, 
                                                        city_name=city_name, seed_number=seed_number, 
                                                        output_dirs=output_dirs, nodes_dict=nodes_dict, network_attrs=network_attrs,
                                                        link_attrs=link_attrs, capacity_tuning_factor=capacity_tuning_factor,
                                                        betweenness_centrality_cutoff=betweenness_centrality_cutoff,
                                                        closeness_centrality_cutoff=closeness_centrality_cutoff,
                                                        hexagon_size=hexagon_size)
        
        #### Check the created networks #######################################################################
        print(f"\nChecking first created scenario: {os.path.basename(first_scenario)}")
        
        #plot the check for the created networks
        matsim_network = plot_check_for_created_networks(
            check_output_subgraph_path=first_scenario,
            zones_gdf=zones_gdf,
            hexagon_grid_all=hexagon_grid_all,
            gdf_edges_with_hex=gdf_edges_with_hex,
            scenario_labels=scenario_labels,
            road_type_subsets=road_type_subsets,
            output_dirs=output_dirs
        )   
        
        #cross check the created networks
        edges_with_road_type, edges_in_hexagons, capacity_changes = cross_check_for_created_networks(
            check_output_subgraph_path=first_scenario,
            gdf_edges_with_hex=gdf_edges_with_hex,
            road_type_subsets=road_type_subsets,
            scenario_labels=scenario_labels,
            seed_number=args.seed_number,
            output_dirs=output_dirs
        )  
        
        #print("\nDetailed Cross-Check Results:")
        #print("\nEdges with matching road type:")
        #print(edges_with_road_type)
        #print("\nEdges in selected hexagons:")
        #print(edges_in_hexagons)
        #print("\nCapacity changes:")
        #print(capacity_changes)
    weighted_mean(target_mean_list, actual_mean_list, subgraph_count_list)
if __name__ == "__main__":
    main()

