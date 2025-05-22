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
city_name = "rosenheim"
hex_size = 500
seed_number = 2
road_type = "primary"
scenario_number = 2
mean = 4
std =8

zones = gpd.read_file(base_dir / "data" / 'city_boundaries' / city_name / f'{city_name}.json')
gdf_basecase_mean = gpd.read_file(base_dir / "data" / "basecases_mean" / city_name / f"{city_name}_basecase_average_output_links.geojson")
gdf_difference = gpd.read_file(base_dir / "data" / "difference_mean" / city_name / f"{city_name}_{road_type}_network_s{scenario_number}_difference_average_output_links.geojson")
gdf_scenario_mean = gpd.read_file(base_dir / "data" / "scenario_mean" / city_name / f"{city_name}_{road_type}_network_s{scenario_number}_scenario_average_output_links.geojson")

# Load hexagon grid
hexagon_grid = gpd.read_file(base_dir / "data" / "subgraph" / "hexagon" / city_name / f"{city_name}_seed_{seed_number}_hex{hex_size}_mean{mean}_std{std}/" / 'data' / f"{city_name}_hexagon_grid.geojson")

# Build the directory path (up to the networks folder)
networks_dir = base_dir / "data" / "subgraph" / "network_files" / city_name / f"{city_name}_seed_{seed_number}_hex{hex_size}_mean{mean}_std{std}" / "networks"

# Build the pattern for files ending with s_{scenario_number}.json
pattern_hexagon_files = f"network_seed{seed_number}_{city_name}_{road_type}_n*_s{scenario_number}_hexagons.json"
pattern_capacity_reduction = f"network_seed{seed_number}_{city_name}_{road_type}_n*_s{scenario_number}_reduced_capacity_edges.geojson"
pattern_all_roadtypes = f"network_seed{seed_number}_{city_name}_{road_type}_n*_s{scenario_number}_edges_of_roadtype.geojson"

# Use glob to find matching files
matching_files = list(networks_dir.glob(pattern_hexagon_files))
matching_files_capacity_reduction = list(networks_dir.glob(pattern_capacity_reduction))
matching_files_all_roadtypes = list(networks_dir.glob(pattern_all_roadtypes))

if matching_files and matching_files_capacity_reduction and matching_files_all_roadtypes:
    scenario_hexagon_file = matching_files[0]  # Take the first match, or handle as needed
    scenario_capacity_reduction_file = matching_files_capacity_reduction[0]
    scenario_all_roadtypes_file = matching_files_all_roadtypes[0]
    gdf_with_capacity_reduction = gpd.read_file(scenario_capacity_reduction_file)
    gdf_with_all_roadtypes_in_scenario = gpd.read_file(scenario_all_roadtypes_file)
else:
    scenario_hexagon_file = None  # Or raise an error, or handle as you wish
    gdf_with_capacity_reduction = None
    gdf_with_all_roadtypes_in_scenario = None
    raise ValueError("No matching files found")

print(f"Selected file for hexagon file: {scenario_hexagon_file}")
print(f"Selected file for capacity reduction: {scenario_capacity_reduction_file}")
print(f"Selected file for all roadtypes in scenario: {scenario_all_roadtypes_file}")

#to adapt
plot_in_percentage = True
zone = 0

def plot_simulation_output(gdf, in_percentage: bool, target_zone: gpd.GeoDataFrame, 
                      scenario_hexagon_file: Path = None, do_save: bool=False,
                      gdf_basecase_mean: gpd.GeoDataFrame = None,
                      gdf_model_output: gpd.GeoDataFrame = None,
                      gdf_with_capacity_reduction: gpd.GeoDataFrame = None,
                      gdf_with_all_roadtypes_in_scenario: gpd.GeoDataFrame = None):
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
    column_to_plot = "vol_car_clipped_percentage_difference" if in_percentage else "vol_car"
    print(f"\nTrying to plot column: {column_to_plot}")
    
    if column_to_plot not in gdf.columns:
        raise ValueError(f"Column {column_to_plot} not found in DataFrame")
    gdf = gpd.GeoDataFrame(gdf, geometry='geometry', crs="EPSG:25832")

    # Set up the plot
    fig, ax = plt.subplots(1, 1, figsize=(20, 20), dpi=800)
    
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
        if (
            gdf_with_capacity_reduction is not None and not gdf_with_capacity_reduction.empty and
            gdf_with_all_roadtypes_in_scenario is not None and not gdf_with_all_roadtypes_in_scenario.empty
        ):
            capacity_reduced_links = set(gdf_with_capacity_reduction['link'].values)
            all_roadtypes_in_scenario_links = set(gdf_with_all_roadtypes_in_scenario['link'].values)
            print(f"Number of all {road_type} links in scenario hexagons: {len(all_roadtypes_in_scenario_links)}")   
            print(f"\nNumber of {road_type} links with capacity reduction in scenario hexagons: {len(capacity_reduced_links)}")
            
            # Separate edges with and without capacity reduction
            reduced_edges = intersecting_data[intersecting_data['link'].isin(capacity_reduced_links)]
            roadtype_edges = intersecting_data[intersecting_data['link'].isin(all_roadtypes_in_scenario_links)]
            normal_edges = intersecting_data[~intersecting_data['link'].isin(capacity_reduced_links) & ~intersecting_data['link'].isin(all_roadtypes_in_scenario_links)]
            
            print(f"Number of reduced edges: {len(reduced_edges)}")
            print(f"Number of normal edges: {len(normal_edges)}")
            
            # Plot normal edges
            if len(normal_edges) > 0:
                print("\nPlotting normal edges...")
                print(f"Normal edges bounds: {normal_edges.total_bounds}")
                try:
                    normal_edges.plot(column=column_to_plot, cmap='coolwarm', linewidth=2, ax=ax, 
                                    norm=norm, label="Roads in target zone", zorder=2,aspect=1)
                except Exception as e:
                    print(f"Error plotting normal edges: {str(e)}")
            
            # Plot capacity-reduced edges with thicker lines
            if len(roadtype_edges) > 0:
                print("\nPlotting roadtype edges...")
                print(f"Roadtype edges bounds: {roadtype_edges.total_bounds}")
                try:
                    roadtype_edges.plot(column=column_to_plot, cmap='coolwarm', linewidth=4, ax=ax,
                                     norm=norm, label="Roads with capacity reduction", zorder=3.5, aspect=1)
                except Exception as e:
                    print(f"Error plotting roadtype edges: {str(e)}")
                print(f"\nNumber of roadtype edges in view: {len(roadtype_edges)}")
                
            if len(reduced_edges) > 0:
                print("\nPlotting reduced edges...")
                print(f"Reduced edges bounds: {reduced_edges.total_bounds}")
                try:
                    # First plot: thick black line (border)
                    reduced_edges.plot(
                        ax=ax, color='black', linewidth=5.2, zorder=4.2,aspect=1
                    )
                    # Second plot: colored line, slightly thinner, on top
                    reduced_edges.plot(
                        column=column_to_plot, cmap='coolwarm', linewidth=4, ax=ax,
                        norm=norm, label="Capacity reduced roads", zorder=5,aspect=1
                    )
                except Exception as e:
                    print(f"Error plotting reduced edges: {str(e)}")
        else:
            # Plot all edges normally if no capacity reduction data
            print("\nPlotting all edges (no capacity reduction data)...")
            try:
                intersecting_data.plot(column=column_to_plot, cmap='coolwarm', linewidth=2.6, ax=ax,
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
    hexagon_grid.plot(ax=ax, color='none', edgecolor='gray', alpha=0.5, linewidth=0.8, zorder=3,aspect=1)
    
    # If scenario hexagon file is provided, highlight selected hexagons
    if scenario_hexagon_file and scenario_hexagon_file.exists():
        with open(scenario_hexagon_file, 'r') as f:
            scenario_data = json.load(f)
            selected_hexagons = scenario_data['hexagon_ids']
            
            # Highlight selected hexagons
            selected_grid = hexagon_grid[hexagon_grid['grid_id'].isin(selected_hexagons)]
            selected_grid.plot(ax=ax, color='none', edgecolor='green', 
                             linewidth=1.2, label=f"Selected Hexagons ({scenario_data['road_type']})", zorder=6,aspect=1)
            
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
    gpd.GeoSeries(outer_boundary, crs=gdf.crs).plot(ax=ax, edgecolor='black', linewidth=2, label="Target Zone", zorder=6,aspect=1)
    
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
        cbar.set_label('Car volume: Difference to base case (%)', fontname='Times New Roman', fontsize=15)
    else:
        cbar.set_label('Car volume: Difference to base case (absolute)', fontname='Times New Roman', fontsize=15)
    
    if do_save:
        plt.savefig("results/difference_to_policies.png", bbox_inches='tight', dpi=600)
    plt.show()

# Example usage:
# To use with hexagon overlay, provide the path to the scenario's hexagon JSON file
plot_simulation_output(gdf_difference, in_percentage=plot_in_percentage, target_zone=zones.iloc[[zone]], 
                      scenario_hexagon_file=scenario_hexagon_file, do_save=False,
                      gdf_basecase_mean=gdf_basecase_mean,
                      gdf_model_output=gdf_scenario_mean,
                      gdf_with_capacity_reduction=gdf_with_capacity_reduction,
                      gdf_with_all_roadtypes_in_scenario=gdf_with_all_roadtypes_in_scenario)

plot_simulation_output(gdf_difference, in_percentage=False, target_zone=zones.iloc[[zone]], 
                      scenario_hexagon_file=scenario_hexagon_file, do_save=False,
                      gdf_basecase_mean=gdf_basecase_mean,
                      gdf_model_output=gdf_scenario_mean,
                      gdf_with_capacity_reduction=gdf_with_capacity_reduction,
                      gdf_with_all_roadtypes_in_scenario=gdf_with_all_roadtypes_in_scenario)