"""
is_capacity_changed_test.py

Purpose
-------
This script compares the 'capacity' attribute of links between two MATSim network files
(original and modified) and reports which links have changed capacity.

Functionality
-------------
- Loads two MATSim network XML files (gzipped) and converts them to GeoDataFrames using
  the `matsim_network_input_to_gdf` function.
- Merges the two networks on link identifiers ('id', 'from', 'to').
- Identifies and reports links whose 'capacity' attribute differs between the original
  and modified networks.
- Prints a summary of the comparison and displays the DataFrame of changed links.

Usage
-----
- Set the `original_file` and `modified_file` variables to the paths of your network files.
- Run the script:
    python is_capacity_changed_test.py
    
Notes
-----
- This script is intended for quick inspection and testing.
"""

# Standard library imports
import sys
import os
import gzip
import logging
import multiprocessing as mp
from collections import Counter
from functools import reduce
from itertools import islice
from pathlib import Path
import random
import re
import json
import argparse

# Add the 'creating_subgraphs' directory to Python path for local imports
current_dir = Path(__file__).resolve().parent
creating_subgraphs_dir = current_dir.parent / "creating_subgraphs"
sys.path.insert(0, str(creating_subgraphs_dir))

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
from hexagon_creation_and_plot import (
    matsim_network_input_to_gdf,
    clean_duplicates_based_on_modes,
    create_nodes_dict,
    multipolygon_to_polygon,
    modify_geodataframe,
    merge_edges_and_zones,
    generate_hexagon_grid,
    merge_edges_and_hexagon_grid,
    consolidate_road_types,
    check_hexagon_statistics,
    plot_grid_and_edges,
    convert_and_save_geodataframe,
    plot_hexagon_grid_with_ids
)
from betweenness_and_closeness import (
    edge_closeness_centrality,
    analyze_centrality_measures,
    create_network_from_csv,
    verify_components
)

### Settings for filepath, working directory and output path #########################################################
# Script is at: bavaria/src/main/python/tests/is_capacity_changed_test.py
# We need to go up 4 levels to reach bavaria directory
base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent

# Load original baseline network
original_file = base_dir / "data/simulation_input/simulation_per_city/fuerth/fuerth_network.xml.gz"

# Load your modified network file  
modified_file = base_dir / "data/subgraph/network_files/fuerth/fuerth_seed_3_hex500_mean4_std8/networks/network_seed3_fuerth_primary_n1_s303.xml.gz"

# Use your existing matsim_network_input_to_gdf function or similar
original_network, _, _, _, _ = matsim_network_input_to_gdf(str(original_file))
modified_network, _, _, _, _ = matsim_network_input_to_gdf(str(modified_file))

# Merge the two networks on link identifiers
comparison = original_network[['id', 'from', 'to', 'capacity']].merge(
    modified_network[['id', 'from', 'to', 'capacity']], 
    on=['id', 'from', 'to'], 
    suffixes=('_original', '_modified')
)

# Check which links have different capacities
comparison['capacity_changed'] = comparison['capacity_original'] != comparison['capacity_modified']

# Count the differences
changed_count = comparison['capacity_changed'].sum()
unchanged_count = (~comparison['capacity_changed']).sum()

# Show summary
print(f"Total links compared: {len(comparison)}")
print(f"Links with changed capacity: {changed_count}")
print(f"Links with same capacity: {unchanged_count}")

# Show the links that changed
changed_links = comparison[comparison['capacity_changed']]
print(f"Changed links:\n{changed_links}")

# Calculate reduction factors (optional)
# changed_links['reduction_factor'] = changed_links['capacity_modified'] / changed_links['capacity_original']