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
from matplotlib.colors import LogNorm
import shapely.wkt as wkt
from shapely.geometry import Point, LineString, box
from shapely.ops import nearest_points
from matplotlib.colors import TwoSlopeNorm
import json
from shapely.ops import unary_union
from mpl_toolkits.axes_grid1 import make_axes_locatable

base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent

zones = gpd.read_file(base_dir / "data" / 'city_boundaries' / 'augsburg' / 'augsburg.json')
gdf_basecase_mean = gpd.read_file(base_dir / "data" / "basecases_mean" / "augsburg" / "augsburg_basecase_average_output_links.geojson")
gdf_basecase_difference = gpd.read_file(base_dir / "data" / "difference_mean" / "augsburg" / "augsburg_secondary_difference_average_output_links.geojson")
gdf_model_output = gpd.read_file(base_dir / "data" / "scenario_mean" / "augsburg" / "augsburg_secondary_scenario_average_output_links.geojson")

# Load hexagon grid
hexagon_grid = gpd.read_file(base_dir / "data" / "subgraph_new_new" / "hexagon" / "augsburg" / "data" / "augsburg_hexagon_grid.geojson")
scenario_hexagon_file = base_dir / "data" / "subgraph_new_new" / "network_files" / "augsburg" / "augsburg_seed_83" / "networks" / "network_1" / "network_seed83_augsburg_secondary_n9_s2_hexagons.json"

#load edges where capacity reduction was applied
gdf_with_capacity_reduction = gpd.read_file(base_dir / "data" / "subgraph_new_new" / "network_files" / "augsburg" / "augsburg_seed_83" / "networks" / "network_1" / "network_seed83_augsburg_secondary_n9_s2_reduced_capacity_edges.geojson")

#to adapt
plot_in_percentage = False
zone = 0

def plot_simulation_output(df, in_percentage: bool, target_zone: gpd.GeoDataFrame, 
                      scenario_hexagon_file: Path = None, do_save: bool=False,
                      gdf_basecase_mean: gpd.GeoDataFrame = None,
                      gdf_model_output: gpd.GeoDataFrame = None,
                      gdf_with_capacity_reduction: gpd.GeoDataFrame = None):
    """
    Plot simulation output with differences to base case and overlay selected hexagons.
    
    Parameters:
    df: GeoDataFrame with simulation results
    in_percentage: bool, whether to show differences in percentage
    target_zone: GeoDataFrame with the target zone geometry
    scenario_hexagon_file: Path to the scenario's hexagon JSON file (optional)
    do_save: bool, whether to save the plot
    gdf_basecase_mean: GeoDataFrame with basecase data
    gdf_model_output: GeoDataFrame with scenario data
    gdf_with_capacity_reduction: GeoDataFrame containing edges where capacity was reduced
    """
    # Convert DataFrame to GeoDataFrame with correct CRS
    column_to_plot = "vol_car" if in_percentage else "vol_car_clipped_percentage_difference"
    print(f"\nTrying to plot column: {column_to_plot}")
    
    if column_to_plot not in df.columns:
        raise ValueError(f"Column {column_to_plot} not found in DataFrame")
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:25832")

    # Set up the plot
    fig, ax = plt.subplots(1, 1, figsize=(20, 20), dpi=600)
    
    # Check intersections with target zone and convert to boolean
    gdf['intersects_target_zone'] = gdf.geometry.apply(
        lambda x: any(x.intersects(zone_geom) for zone_geom in target_zone.geometry)
    ).astype(bool)
    
    # Debug: Print intersection info
    intersection_counts = gdf['intersects_target_zone'].value_counts()
    print("\nIntersection counts:")
    print(intersection_counts)
    print(f"Number of intersecting roads: {intersection_counts.get(True, 0)}")
    
    # Make sure the column to plot is numeric
    if not pd.api.types.is_numeric_dtype(gdf[column_to_plot]):
        print(f"\nWarning: Converting {column_to_plot} to numeric")
        gdf[column_to_plot] = pd.to_numeric(gdf[column_to_plot], errors='coerce')
    
    # Filter out any NaN values
    #gdf = gdf.dropna(subset=[column_to_plot])
    
    # Debug: Print final data info
    print("\nFinal data shape after cleaning:", gdf.shape)
    print("Final data sample:")
    print(gdf[[column_to_plot]].head())
    
    # Use TwoSlopeNorm for custom normalization
    norm = TwoSlopeNorm(vmin=gdf[column_to_plot].min(), vcenter=gdf[column_to_plot].median(), vmax=gdf[column_to_plot].max())
    
    # Plot the edges that intersect with target zone
    intersecting_data = gdf[gdf['intersects_target_zone']]
    print(f"\nNumber of intersecting edges: {len(intersecting_data)}")
    print(f"Intersecting data bounds: {intersecting_data.total_bounds if len(intersecting_data) > 0 else 'No bounds'}")
    
    if len(intersecting_data) > 0:
        # If we have capacity reduction data, split the intersecting data into two parts
        if gdf_with_capacity_reduction is not None:
            capacity_reduced_links = set(gdf_with_capacity_reduction['link'].values)
            print(f"\nNumber of capacity reduced links: {len(capacity_reduced_links)}")
            
            # Separate edges with and without capacity reduction
            reduced_edges = intersecting_data[intersecting_data['link'].isin(capacity_reduced_links)]
            normal_edges = intersecting_data[~intersecting_data['link'].isin(capacity_reduced_links)]
            
            print(f"Number of reduced edges: {len(reduced_edges)}")
            print(f"Number of normal edges: {len(normal_edges)}")
            
            # Plot normal edges
            if len(normal_edges) > 0:
                print("\nPlotting normal edges...")
                print(f"Normal edges bounds: {normal_edges.total_bounds}")
                try:
                    normal_edges.plot(column=column_to_plot, cmap='coolwarm', linewidth=1.3, ax=ax, 
                                    norm=norm, label="Roads in target zone", zorder=2)
                except Exception as e:
                    print(f"Error plotting normal edges: {str(e)}")
            
            # Plot capacity-reduced edges with thicker lines
            if len(reduced_edges) > 0:
                print("\nPlotting reduced edges...")
                print(f"Reduced edges bounds: {reduced_edges.total_bounds}")
                try:
                    reduced_edges.plot(column=column_to_plot, cmap='coolwarm', linewidth=2.6, ax=ax,
                                     norm=norm, label="Roads with capacity reduction", zorder=3, aspect=1)
                except Exception as e:
                    print(f"Error plotting reduced edges: {str(e)}")
                print(f"\nNumber of capacity-reduced edges in view: {len(reduced_edges)}")
        else:
            # Plot all edges normally if no capacity reduction data
            print("\nPlotting all edges (no capacity reduction data)...")
            try:
                intersecting_data.plot(column=column_to_plot, cmap='coolwarm', linewidth=1.3, ax=ax,
                                     norm=norm, label="Roads in target zone", zorder=2)
            except Exception as e:
                print(f"Error plotting all edges: {str(e)}")
        
        # Calculate total volume statistics for intersecting roads
        intersecting_links = intersecting_data['link'].tolist()
        
        # Get the corresponding data from basecase and scenario
        basecase_intersecting = gdf_basecase_mean[gdf_basecase_mean['link'].isin(intersecting_links)]
        scenario_intersecting = gdf_model_output[gdf_model_output['link'].isin(intersecting_links)]
        
        # Calculate total volumes
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
    
    
    # Plot hexagon grid
    hexagon_grid.plot(ax=ax, color='none', edgecolor='gray', alpha=0.3, linewidth=0.5, zorder=3)
    
    # If scenario hexagon file is provided, highlight selected hexagons
    if scenario_hexagon_file and scenario_hexagon_file.exists():
        with open(scenario_hexagon_file, 'r') as f:
            scenario_data = json.load(f)
            selected_hexagons = scenario_data['hexagon_ids']
            
            # Highlight selected hexagons
            selected_grid = hexagon_grid[hexagon_grid['grid_id'].isin(selected_hexagons)]
            selected_grid.plot(ax=ax, color='none', edgecolor='green', 
                             linewidth=1.3, label=f"Selected Hexagons ({scenario_data['road_type']})", zorder=4)
            
            # Add hexagon IDs as labels for selected hexagons
            for _, row in selected_grid.iterrows():
                centroid = row.geometry.centroid
                ax.text(centroid.x, centroid.y, str(row['grid_id']), 
                        horizontalalignment='center',
                        verticalalignment='center',
                        fontsize=8,
                        bbox=dict(facecolor='none', alpha=0, edgecolor='none'),
                        zorder=5)
    
    # Add buffer to target zone to avoid overlapping with edges
    buffered_zone = target_zone.copy()
    
    # Create a single outer boundary
    outer_boundary = unary_union(buffered_zone.geometry).boundary
    
    # Plot only the outer boundary
    gpd.GeoSeries(outer_boundary, crs=gdf.crs).plot(ax=ax, edgecolor='black', linewidth=2, label="Target Zone", zorder=6)
    
    plt.xlabel("X Coordinate", fontname='Times New Roman', fontsize=15)
    plt.ylabel("Y Coordinate", fontname='Times New Roman', fontsize=15)
    
    ax.tick_params(axis='both', which='major', labelsize=10)
    for label in (ax.get_xticklabels() + ax.get_yticklabels()):
        label.set_fontname('Times New Roman')
        label.set_fontsize(15)
    
    # Add legend inside the plot in the upper right corner
    ax.legend(prop={'family': 'Times New Roman', 'size': 15}, 
             loc='upper right',
             bbox_to_anchor=(1.0, 1.0),
             framealpha=0.9,
             facecolor='white',
             edgecolor='black')
    
    cax = fig.add_axes([0.87, 0.22, 0.03, 0.5])
    
    sm = plt.cm.ScalarMappable(cmap='coolwarm', norm=norm)
    sm._A = []
    cbar = plt.colorbar(sm, cax=cax)
    
    cbar.ax.tick_params(labelsize=15)
    for t in cbar.ax.get_yticklabels():
        t.set_fontname('Times New Roman')
    cbar.ax.yaxis.label.set_fontname('Times New Roman')
    cbar.ax.yaxis.label.set_size(15)
    
    if in_percentage:
        cbar.set_label('Car volume: Difference to base case (absolute))', fontname='Times New Roman', fontsize=15)
    else:
        cbar.set_label('Car volume: Difference to base case (%)', fontname='Times New Roman', fontsize=15)
    
    if do_save:
        plt.savefig("results/difference_to_policies.png", bbox_inches='tight', dpi=600)
    plt.show()

# Example usage:
# To use with hexagon overlay, provide the path to the scenario's hexagon JSON file
plot_simulation_output(gdf_basecase_difference, in_percentage=plot_in_percentage, target_zone=zones.iloc[[zone]], 
                      scenario_hexagon_file=scenario_hexagon_file, do_save=False,
                      gdf_basecase_mean=gdf_basecase_mean,
                      gdf_model_output=gdf_model_output,
                      gdf_with_capacity_reduction=gdf_with_capacity_reduction)
