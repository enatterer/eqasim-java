"""
Comprehensive Visualization Module for MATSim Network Intervention Analysis

This module creates sophisticated comparative visualizations showing the impact of network
interventions on traffic patterns. It overlays scenario results with baseline conditions,
highlighting affected hexagons and road segments with capacity reductions.

Key Features:
    1. Side-by-side comparison of baseline vs scenario traffic volumes
    2. Color-coded visualization of traffic volume changes (absolute/percentage)
    3. Hexagon grid overlay showing intervention areas
    4. Detailed road segment highlighting based on intervention type
    5. Statistical summaries of intervention impacts

Visualization Components:
    - Base network: All roads in target zone (thin lines)
    - Target road types: Roads of intervention type in hexagons (medium lines)  
    - Capacity-reduced roads: Roads with actual capacity reduction (thick lines with borders)
    - Selected hexagons: Intervention area boundaries (green outlines)
    - Zone boundaries: Study area limits (black outlines)

Configuration:
    Modify global variables for different scenarios:
    - city_name: Target city for analysis
    - hex_size, seed_number: Hexagon grid parameters
    - road_type, scenario_number: Intervention specifications
    - plot_in_percentage: Toggle between absolute/percentage change visualization

Usage:
    python3 comparison_plot.py
    
    # Generates two plots automatically:
    # 1. Percentage change visualization
    # 2. Absolute change visualization

Requirements:
    - Baseline data: data/basecases_mean/<city>/
    - Scenario data: data/scenario_mean/<city>/ and data/difference_mean/<city>/
    - Hexagon grids: data/subgraph/hexagon/<city>/
    - Network files: data/subgraph/network_files/<city>/
    - City boundaries: data/city_boundaries/<city>/
"""

import geopandas as gpd
import os
import glob
import gzip
import math
import random
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from matplotlib.colors import LogNorm, TwoSlopeNorm
import shapely.wkt as wkt
from shapely.geometry import Point, LineString, box
from shapely.ops import nearest_points
from matplotlib.colors import TwoSlopeNorm
import json
from shapely.ops import unary_union
from mpl_toolkits.axes_grid1 import make_axes_locatable

# Configuration parameters - modify these for different scenarios
base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
city_name = "erlangen"
hex_size = 500
seed_number = 3
road_type = "primary"
scenario_number = 283
mean = 4
std = 8
# Visualization settings
plot_in_percentage = True
zone = 0  # Zone index to visualize (0 = first zone)

# Data loading - all required datasets for visualization
zones = gpd.read_file(base_dir / "data" / 'city_boundaries' / city_name / f'{city_name}.json')
gdf_basecase_mean = gpd.read_file(base_dir / "data" / "basecases_mean" / city_name / f"{city_name}_basecase_average_output_links.geojson")
gdf_difference = gpd.read_file(base_dir / "data" / "difference_mean" / city_name / f"{city_name}_{road_type}_network_s{scenario_number}_difference_average_output_links.geojson")
gdf_scenario_mean = gpd.read_file(base_dir / "data" / "scenario_mean" / city_name / f"{city_name}_{road_type}_network_s{scenario_number}_scenario_average_output_links.geojson")

# Load hexagon grid and scenario-specific files
hexagon_grid = gpd.read_file(base_dir / "data" / "subgraph" / "hexagon" / city_name / f"{city_name}_seed_{seed_number}_hex{hex_size}_mean{mean}_std{std}/" / 'data' / f"{city_name}_hexagon_grid.geojson")

# Build paths and patterns for scenario-specific files
networks_dir = base_dir / "data" / "subgraph" / "network_files" / city_name / f"{city_name}_seed_{seed_number}_hex{hex_size}_mean{mean}_std{std}" / "networks"
pattern_hexagon_files = f"network_seed{seed_number}_{city_name}_{road_type}_n*_s{scenario_number}_hexagons.json"
pattern_capacity_reduction = f"network_seed{seed_number}_{city_name}_{road_type}_n*_s{scenario_number}_reduced_capacity_edges.geojson"
pattern_all_roadtypes = f"network_seed{seed_number}_{city_name}_{road_type}_n*_s{scenario_number}_edges_of_roadtype.geojson"

# Find and load scenario-specific files
matching_files = list(networks_dir.glob(pattern_hexagon_files))
matching_files_capacity_reduction = list(networks_dir.glob(pattern_capacity_reduction))
matching_files_all_roadtypes = list(networks_dir.glob(pattern_all_roadtypes))

if matching_files and matching_files_capacity_reduction and matching_files_all_roadtypes:
    scenario_hexagon_file = matching_files[0]
    scenario_capacity_reduction_file = matching_files_capacity_reduction[0]
    scenario_all_roadtypes_file = matching_files_all_roadtypes[0]
    gdf_with_capacity_reduction = gpd.read_file(scenario_capacity_reduction_file)
    gdf_with_all_roadtypes_in_scenario = gpd.read_file(scenario_all_roadtypes_file)
else:
    raise ValueError("No matching scenario files found. Check file paths and naming patterns.")

print(f"Selected file for hexagon file: {scenario_hexagon_file}")
print(f"Selected file for capacity reduction: {scenario_capacity_reduction_file}")
print(f"Selected file for all roadtypes in scenario: {scenario_all_roadtypes_file}")

def plot_simulation_output(gdf, in_percentage: bool, target_zone: gpd.GeoDataFrame, 
                          scenario_hexagon_file: Path = None, do_save: bool = False,
                          gdf_basecase_mean: gpd.GeoDataFrame = None,
                          gdf_model_output: gpd.GeoDataFrame = None,
                          gdf_with_capacity_reduction: gpd.GeoDataFrame = None,
                          gdf_with_all_roadtypes_in_scenario: gpd.GeoDataFrame = None):
    """
    Create comprehensive visualization of network intervention impacts.
    
    Generates sophisticated plots showing traffic volume changes between baseline
    and scenario conditions, with detailed highlighting of intervention areas
    and affected road segments.
    
    Visualization Layers (bottom to top):
        1. Hexagon grid (gray outlines, background reference)
        2. Normal roads in zone (thin colored lines)
        3. Target road type in hexagons (medium colored lines)
        4. Capacity-reduced roads (thick colored lines with black borders)
        5. Selected hexagons (green outlines)
        6. Zone boundaries (black outlines)
    
    Args:
        gdf (GeoDataFrame): Difference analysis data with traffic volume changes
        in_percentage (bool): If True, plots percentage changes; if False, absolute changes
        target_zone (GeoDataFrame): Zone boundaries for spatial filtering
        scenario_hexagon_file (Path, optional): JSON file with selected hexagon IDs
        do_save (bool, optional): Whether to save plot to file. Defaults to False
        gdf_basecase_mean (GeoDataFrame, optional): Baseline traffic data for statistics
        gdf_model_output (GeoDataFrame, optional): Scenario traffic data for statistics  
        gdf_with_capacity_reduction (GeoDataFrame, optional): Roads with capacity reduction
        gdf_with_all_roadtypes_in_scenario (GeoDataFrame, optional): All target roads in hexagons
        
    Displays:
        Interactive matplotlib plot with:
        - Color-coded traffic volume changes using diverging colormap
        - Custom legend explaining different road categories
        - Colorbar showing change magnitude
        - Hexagon ID labels for selected intervention areas
        
    Prints:
        Comprehensive statistics including:
        - Number of roads in each category
        - Total traffic volume changes (absolute and percentage)
        - Road network length statistics
        - Intervention coverage metrics
        
    Raises:
        ValueError: If required column not found in input data
        FileNotFoundError: If scenario hexagon file doesn't exist when provided
        
    Note:
        Uses TwoSlopeNorm for balanced color scaling around median values
        Coordinates system: EPSG:25832 (appropriate for German cities)
    """
    # Determine which column to plot based on percentage preference
    column_to_plot = "vol_car_clipped_percentage_difference" if in_percentage else "vol_car"
    print(f"\nTrying to plot column: {column_to_plot}")
    
    if column_to_plot not in gdf.columns:
        raise ValueError(f"Column {column_to_plot} not found in DataFrame")
    gdf = gpd.GeoDataFrame(gdf, geometry='geometry', crs="EPSG:25832")

    # Set up high-resolution figure for publication quality
    fig, ax = plt.subplots(1, 1, figsize=(20, 20), dpi=800)
    
    # Spatial filtering: identify roads intersecting with target zone
    gdf['intersects_target_zone'] = gdf.geometry.apply(
        lambda x: any(x.intersects(zone_geom) for zone_geom in target_zone.geometry)
    ).astype(bool)
    
    # Debug information for spatial intersection
    intersection_counts = gdf['intersects_target_zone'].value_counts()
    print("\nIntersection counts:")
    print(intersection_counts)
    print(f"Number of intersecting roads: {intersection_counts.get(True, 0)}")
    
    # Ensure numeric data type for plotting column
    if not pd.api.types.is_numeric_dtype(gdf[column_to_plot]):
        print(f"\nWarning: Converting {column_to_plot} to numeric")
        gdf[column_to_plot] = pd.to_numeric(gdf[column_to_plot], errors='coerce')
    
    # Data quality check
    print(f"\nData Quality Check:")
    print(f"Final data shape: {gdf.shape}")
    print(f"Non-null values in {column_to_plot}: {gdf[column_to_plot].notna().sum()}")
    print(f"Data range: {gdf[column_to_plot].min():.2f} to {gdf[column_to_plot].max():.2f}")
    
    # Create balanced color normalization around median
    norm = TwoSlopeNorm(
        vmin=gdf[column_to_plot].min(), 
        vcenter=gdf[column_to_plot].median(), 
        vmax=gdf[column_to_plot].max()
    )
    
    # Filter to roads intersecting target zone
    intersecting_data = gdf[gdf['intersects_target_zone']]
    print(f"\nNumber of intersecting edges: {len(intersecting_data)}")
    print(f"Intersecting data bounds: {intersecting_data.total_bounds if len(intersecting_data) > 0 else 'No bounds'}")
    
    if len(intersecting_data) > 0:
        # Categorize roads based on intervention type
        if (gdf_with_capacity_reduction is not None and not gdf_with_capacity_reduction.empty and
            gdf_with_all_roadtypes_in_scenario is not None and not gdf_with_all_roadtypes_in_scenario.empty):
            
            # Create sets for efficient lookup
            capacity_reduced_links = set(gdf_with_capacity_reduction['link'].values)
            all_roadtypes_in_scenario_links = set(gdf_with_all_roadtypes_in_scenario['link'].values)
            print(f"Number of all {road_type} links in scenario hexagons: {len(all_roadtypes_in_scenario_links)}")   
            print(f"\nNumber of {road_type} links with capacity reduction in scenario hexagons: {len(capacity_reduced_links)}")
            
            # Separate roads by intervention category
            reduced_edges = intersecting_data[intersecting_data['link'].isin(capacity_reduced_links)]
            roadtype_edges = intersecting_data[intersecting_data['link'].isin(all_roadtypes_in_scenario_links)]
            normal_edges = intersecting_data[~intersecting_data['link'].isin(capacity_reduced_links) & ~intersecting_data['link'].isin(all_roadtypes_in_scenario_links)]
            
            print(f"Number of reduced edges: {len(reduced_edges)}")
            print(f"Number of normal edges: {len(normal_edges)}")
            
            # Layer 1: Plot normal roads (baseline layer)
            if len(normal_edges) > 0:
                print("\nPlotting normal edges...")
                print(f"Normal edges bounds: {normal_edges.total_bounds}")
                try:
                    normal_edges.plot(column=column_to_plot, cmap='coolwarm', linewidth=2, ax=ax, 
                                    norm=norm, label="All roads inside zone", zorder=2,aspect=1)
                except Exception as e:
                    print(f"Error plotting normal edges: {str(e)}")
            
            # Layer 2: Plot target road type in hexagons (medium emphasis)
            if len(roadtype_edges) > 0:
                print("\nPlotting roadtype edges...")
                print(f"Roadtype edges bounds: {roadtype_edges.total_bounds}")
                try:
                    roadtype_edges.plot(column=column_to_plot, cmap='coolwarm', linewidth=4, ax=ax,
                                     norm=norm, label="Target Road Types in hexagons", zorder=3.5, aspect=1)
                except Exception as e:
                    print(f"Error plotting roadtype edges: {str(e)}")
                print(f"\nNumber of roadtype edges in view: {len(roadtype_edges)}")
                
            if len(reduced_edges) > 0:
                print("\nPlotting reduced edges...")
                print(f"Reduced edges bounds: {reduced_edges.total_bounds}")
                try:
                    # Black border for contrast
                    reduced_edges.plot(
                        ax=ax, color='black', linewidth=5.2, zorder=4.2, aspect=1
                    )
                    # Colored top layer
                    reduced_edges.plot(
                        column=column_to_plot, cmap='coolwarm', linewidth=4, ax=ax,
                        norm=norm, label="Target Road Types in hexagons(capacity reduced)", zorder=5,aspect=1
                    )
                except Exception as e:
                    print(f"Error plotting reduced edges: {str(e)}")
        else:
            # Plot all edges normally if no capacity reduction data
            print("\nPlotting all edges (no capacity reduction data)...")
            try:
                intersecting_data.plot(
                    column=column_to_plot, cmap='coolwarm', linewidth=2.6, ax=ax,
                    norm=norm, label="Roads in zone", zorder=2, aspect=1
                )
            except Exception as e:
                print(f"Error plotting all edges: {str(e)}")
        
        # Calculate total volume statistics for intersecting roads
        intersecting_links = intersecting_data['link'].tolist()
        
        # Get the corresponding data from basecase and scenario
        basecase_intersecting = gdf_basecase_mean[gdf_basecase_mean['link'].isin(intersecting_links)]
        scenario_intersecting = gdf_model_output[gdf_model_output['link'].isin(intersecting_links)]
        
        # Traffic volume impact analysis
        total_volume_basecase = basecase_intersecting['vol_car'].sum()
        total_volume_scenario = scenario_intersecting['vol_car'].sum()
        volume_difference = total_volume_scenario - total_volume_basecase
        volume_difference_percentage = (volume_difference / total_volume_basecase) * 100 if total_volume_basecase > 0 else 0
        # Calculate total road network length in stadt
        total_road_network_length_in_stadt_in_basecase = basecase_intersecting['length'].sum()
        total_road_network_length_in_stadt_in_scenario = scenario_intersecting['length'].sum()
        
        # Calculate road network lentght where capacity reduction was applied   
        total_road_network_length_in_stadt_with_capacity_reduction_in_scenario = gdf_with_capacity_reduction['length'].sum()
        
        print(f"Total road network length in stadt in basecase: {total_road_network_length_in_stadt_in_basecase:,.2f}")
        print(f"Total road network length in stadt in scenario: {total_road_network_length_in_stadt_in_scenario:,.2f}")
        print(f"Total road network length in stadt with capacity reduction: {total_road_network_length_in_stadt_with_capacity_reduction_in_scenario:,.2f}")
        print(f'Percentage of road network length in stadt with capacity reduction: {total_road_network_length_in_stadt_with_capacity_reduction_in_scenario / total_road_network_length_in_stadt_in_basecase * 100:.2f}%')
        print("\nTotal Volume Statistics for Intersecting Roads:")
        print(f"Total car volume in scenario: {total_volume_scenario:,.2f}")
        print(f"Total car volume in basecase: {total_volume_basecase:,.2f}")
        print(f"Total volume difference: {volume_difference:,.2f} ({volume_difference_percentage:.2f}%)")
    else:
        print("\nWarning: No roads intersect with the target zone")
    
    # Layer 4: Add hexagon grid as reference (subtle background)
    hexagon_grid.plot(
        ax=ax, color='none', edgecolor='gray', alpha=0.5, 
        linewidth=0.8, zorder=3, aspect=1
    )
    
    # Layer 5: Highlight selected hexagons if scenario file provided
    if scenario_hexagon_file and scenario_hexagon_file.exists():
        try:
            with open(scenario_hexagon_file, 'r') as f:
                scenario_data = json.load(f)
                selected_hexagons = scenario_data['hexagon_ids']
                
            # Highlight intervention hexagons
            selected_grid = hexagon_grid[hexagon_grid['grid_id'].isin(selected_hexagons)]
            selected_grid.plot(
                ax=ax, color='none', edgecolor='green', 
                linewidth=1.2, label=f"Selected hexagons ({scenario_data['road_type']})", 
                zorder=6, aspect=1
            )
            
            # Add hexagon ID labels for reference
            for _, row in selected_grid.iterrows():
                centroid = row.geometry.centroid
                ax.text(
                    centroid.x, centroid.y, str(row['grid_id']), 
                    horizontalalignment='center', verticalalignment='center',
                    fontsize=8, bbox=dict(facecolor='none', alpha=0, edgecolor='none'),
                    zorder=7
                )
                
            print(f"\nHighlighted {len(selected_hexagons)} intervention hexagons")
        except Exception as e:
            print(f"Warning: Could not load scenario hexagon file: {str(e)}")
    
    # Layer 6: Add zone boundaries (top layer for clear delineation)
    outer_boundary = unary_union(target_zone.geometry).boundary
    gpd.GeoSeries(outer_boundary, crs=gdf.crs).plot(
        ax=ax, edgecolor='black', linewidth=2, 
        label="Zone boundary", zorder=8, aspect=1
    )
    
    # Configure plot aesthetics for publication quality
    plt.xlabel("X Coordinate (EPSG:25832)", fontname='Times New Roman', fontsize=15)
    plt.ylabel("Y Coordinate (EPSG:25832)", fontname='Times New Roman', fontsize=15)
    
    # Set tick parameters
    ax.tick_params(axis='both', which='major', labelsize=12)
    for label in (ax.get_xticklabels() + ax.get_yticklabels()):
        label.set_fontname('Times New Roman')
        label.set_fontsize(12)
    
    # Add comprehensive legend
    ax.legend(
        prop={'family': 'Times New Roman', 'size': 13}, 
        loc='upper right', bbox_to_anchor=(0.98, 0.98),
        framealpha=0.95, facecolor='white', edgecolor='black'
    )
    
    # Add custom colorbar
    cax = fig.add_axes([0.87, 0.22, 0.03, 0.5])
    sm = plt.cm.ScalarMappable(cmap='coolwarm', norm=norm)
    sm._A = []
    cbar = plt.colorbar(sm, cax=cax)
    
    # Configure colorbar aesthetics
    cbar.ax.tick_params(labelsize=13)
    for t in cbar.ax.get_yticklabels():
        t.set_fontname('Times New Roman')
    cbar.ax.yaxis.label.set_fontname('Times New Roman')
    cbar.ax.yaxis.label.set_size(15)
    
    # Set colorbar label based on visualization type
    if in_percentage:
        cbar.set_label(
            'Traffic Volume Change (%)', 
            fontname='Times New Roman', fontsize=14
        )
    else:
        cbar.set_label(
            'Traffic Volume Change (vehicles/hour)', 
            fontname='Times New Roman', fontsize=14
        )
    
    # Save high-resolution plot if requested
    if do_save:
        output_path = f"results/{city_name}_{road_type}_s{scenario_number}_{'percentage' if in_percentage else 'absolute'}_comparison.png"
        plt.savefig(output_path, bbox_inches='tight', dpi=600, facecolor='white')
        print(f"\nPlot saved to: {output_path}")
    
    plt.show()


if __name__ == "__main__":
    """
    Main execution block for creating comparative visualizations.
    
    Generates two comprehensive plots for the configured scenario:
    1. Percentage change visualization (relative impact)
    2. Absolute change visualization (absolute impact)
    
    Both plots include full intervention context with hexagon overlays,
    road categorization, and comprehensive statistical summaries.
    
    Configuration is controlled by global variables at the top of the file.
    Modify city_name, scenario_number, road_type, etc. for different analyses.
    """
    print(f"Creating comparative visualizations for {city_name} {road_type} scenario {scenario_number}")
    print(f"Hexagon configuration: seed {seed_number}, size {hex_size}, mean {mean}, std {std}")
    
    # Generate percentage change visualization
    print(f"\n" + "="*50)
    print("GENERATING PERCENTAGE CHANGE VISUALIZATION")
    print("="*50)
    plot_simulation_output(
        gdf_difference, in_percentage=True, target_zone=zones.iloc[[zone]], 
        scenario_hexagon_file=scenario_hexagon_file, do_save=False,
        gdf_basecase_mean=gdf_basecase_mean, gdf_model_output=gdf_scenario_mean,
        gdf_with_capacity_reduction=gdf_with_capacity_reduction,
        gdf_with_all_roadtypes_in_scenario=gdf_with_all_roadtypes_in_scenario
    )
    
    # Generate absolute change visualization  
    print(f"\n" + "="*50)
    print("GENERATING ABSOLUTE CHANGE VISUALIZATION")
    print("="*50)
    plot_simulation_output(
        gdf_difference, in_percentage=False, target_zone=zones.iloc[[zone]], 
        scenario_hexagon_file=scenario_hexagon_file, do_save=False,
        gdf_basecase_mean=gdf_basecase_mean, gdf_model_output=gdf_scenario_mean,
        gdf_with_capacity_reduction=gdf_with_capacity_reduction,
        gdf_with_all_roadtypes_in_scenario=gdf_with_all_roadtypes_in_scenario
    )
    
    print(f"\nVisualization analysis complete!")