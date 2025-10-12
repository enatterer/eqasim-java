"""
Scenario Analysis and Comparison Module for MATSim Network Intervention Results

This module processes MATSim simulation results from network intervention scenarios
to compute statistical measures, create averaged datasets, and compare against baseline
conditions. It analyzes the impact of capacity reductions on traffic volumes and travel patterns.

Key Operations:
    1. Load scenario simulation output files from intervention runs
    2. Compute mean traffic volumes and trip statistics for scenarios
    3. Calculate difference metrics between scenario and baseline conditions
    4. Generate comparative visualizations and statistical summaries
    5. Save processed scenario data and difference analysis

Configuration:
    Modify global variables at the top:
    - city_name: Target city for analysis
    - hex_size: Hexagon grid size used in scenario
    - seed_number: Random seed for reproducibility
    - road_type: Road type targeted in intervention (e.g., 'primary')
    - scenario_number: Specific scenario identifier

Output Files:
    - <city>_<road_type>_network_s<scenario>_scenario_average_output_links.geojson: Averaged scenario network
    - <city>_<road_type>_network_s<scenario>_difference_average_output_links.geojson: Difference from baseline
    - <city>_<road_type>_network_s<scenario>_scenario_average_trips.csv: Mode-specific trip statistics
    - <city>_<road_type>_network_s<scenario>_traffic_volume_map.png: Traffic volume visualization

Usage:
    python3 create_scenario_means.py
    
    # Processes single scenario defined by global variables
    # Reads from: data/simulation_output/scenarios_new/<city>_<road_type>_network_s<scenario>/
    # Outputs to: data/scenario_mean/<city>/ and data/difference_mean/<city>/

Requirements:
    - MATSim scenario simulation output files (output_links.csv.gz, eqasim_trips.csv)
    - Corresponding baseline data in data/basecases_mean/<city>/
    - Consistent network structure between baseline and scenario runs
"""

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

import matplotlib.pyplot as plt


city_name = "erlangen"
hex_size = 500
seed_number = 3
road_type = "primary"
scenario_number = 283

base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
scenario_subdir_path = base_dir / "data" / "simulation_output" / "scenarios_new" / f"{city_name}_{road_type}_network_s{scenario_number}"
result_path_difference = base_dir / "data" / "difference_mean"


def create_dic_seed_to_output_links(subdir):
    """
    Load scenario output_links file into a dictionary structure.
    
    Reads compressed CSV file containing network link data from scenario
    simulation run and converts to GeoDataFrame format.
    
    Args:
        subdir (Path): Directory containing scenario simulation output files
        
    Returns:
        dict: Single-entry dictionary with key '1' mapping to GeoDataFrame
              containing network links and traffic volumes from scenario run
              
    Note:
        Uses '1' as dictionary key for consistency with multi-seed processing patterns
        Returns empty dict if output_links.csv.gz file not found
    """
    result_dic = {}
    output_links_path = scenario_subdir_path / 'output_links.csv.gz'
    if output_links_path.exists():
        df_output_links = pd.read_csv(output_links_path, delimiter=';', low_memory=False)
        if 'geometry' in df_output_links.columns:
            df_output_links['geometry'] = gpd.GeoSeries.from_wkt(df_output_links['geometry'])
            gdf_output_links = gpd.GeoDataFrame(df_output_links, geometry='geometry')
            result_dic['1'] = gdf_output_links
    return result_dic


def create_dic_seed_to_eqasim_trips_given_output_trips(subdir):
    """
    Load scenario eqasim_trips file into a dictionary structure.
    
    Reads trip data file containing detailed trip information from scenario
    simulation run for travel pattern analysis.
    
    Args:
        subdir (Path): Directory containing scenario simulation output files
        
    Returns:
        dict: Single-entry dictionary with key '1' mapping to DataFrame
              containing trip data (travel times, distances, modes) from scenario run
              
    Note:
        Uses '1' as dictionary key for consistency with multi-seed processing patterns
        Returns empty dict if eqasim_trips.csv file not found
    """
    result_dic = {}
    eqasim_trips_path = scenario_subdir_path / 'eqasim_trips.csv'
    if eqasim_trips_path.exists():
        df_eqasim_trips = pd.read_csv(eqasim_trips_path, delimiter=';')
        result_dic['1'] = df_eqasim_trips
    return result_dic
    

def compute_average_or_median_geodataframe(geodataframes, column_name, is_mean: bool = True):
    """
    Compute statistical measures across multiple GeoDataFrames for a specified column.
    
    Calculates either mean or median values for a numeric column across multiple
    data sources, maintaining the spatial structure of the original data.
    
    Args:
        geodataframes (list): List of GeoDataFrames with identical structure
        column_name (str): Column name for statistical computation
        is_mean (bool, optional): If True computes mean, else median. Defaults to True
        
    Returns:
        GeoDataFrame: Copy of first input GeoDataFrame with updated statistical values
                     in the specified column, preserving geometry and other columns
                     
    Note:
        For single scenario analysis, this maintains consistency with multi-run processing
        All input GeoDataFrames must have identical structure and row ordering
    """
    average_gdf = geodataframes[0].copy()
    column_values = np.array([gdf[column_name].values for gdf in geodataframes])
    
    if is_mean:
        column_average = np.mean(column_values, axis=0)
    else:
        column_average = np.median(column_values, axis=0)

    average_gdf[column_name] = column_average
    return average_gdf    


def create_scenario_output_links_mean_file(city_name, gdf_scenario_mean, road_type):
    """
    Save averaged scenario network data as GeoJSON file.
    
    Creates directory structure and saves the scenario network with traffic
    volumes and intervention effects for further analysis.
    
    Args:
        city_name (str): Name of the city for file naming
        gdf_scenario_mean (GeoDataFrame): Averaged scenario network data to save
        road_type (str): Road type targeted in intervention (e.g., 'primary')
        
    Saves:
        GeoJSON file at: data/scenario_mean/<city>/<city>_<road_type>_network_s<scenario>_scenario_average_output_links.geojson
    """
    result_path_scenario_mean = base_dir / "data" / "scenario_mean" / city_name / f"{city_name}_{road_type}_network_s{scenario_number}_scenario_average_output_links.geojson"
    result_path_scenario_mean.parent.mkdir(parents=True, exist_ok=True)
    gdf_scenario_mean.to_file(result_path_scenario_mean, driver='GeoJSON')


def create_difference_output_links_mean_file(city_name, gdf_difference_mean, road_type):
    """
    Save difference analysis between scenario and baseline as GeoJSON file.
    
    Creates directory structure and saves the difference metrics showing
    intervention impacts compared to baseline conditions.
    
    Args:
        city_name (str): Name of the city for file naming
        gdf_difference_mean (GeoDataFrame): Difference analysis data to save
        road_type (str): Road type targeted in intervention (e.g., 'primary')
        
    Saves:
        GeoJSON file at: data/difference_mean/<city>/<city>_<road_type>_network_s<scenario>_difference_average_output_links.geojson
    """
    result_path_difference = base_dir / "data" / "difference_mean" / city_name / f"{city_name}_{road_type}_network_s{scenario_number}_difference_average_output_links.geojson"
    result_path_difference.parent.mkdir(parents=True, exist_ok=True)
    gdf_difference_mean.to_file(result_path_difference, driver='GeoJSON')


def plot_scenario_mean_file(city_name, road_type): 
    """
    Create and save traffic volume visualization for scenario results.
    
    Generates a high-resolution map showing car traffic volumes across the
    network after intervention, with color coding and basic statistics.
    
    Args:
        city_name (str): Name of the city for plot title and file naming
        road_type (str): Road type targeted in intervention for file naming
        
    Saves:
        PNG file at: data/scenario_mean/<city>/<city>_<road_type>_network_s<scenario>_traffic_volume_map.png
        
    Prints:
        File save location and traffic volume statistics summary
        
    Note:
        Reads GeoJSON file created by create_scenario_output_links_mean_file()
    """
    geojson_path = base_dir / "data" / "scenario_mean" / city_name / f"{city_name}_{road_type}_network_s{scenario_number}_scenario_average_output_links.geojson"
    gdf = gpd.read_file(geojson_path)

    fig, ax = plt.subplots(figsize=(15, 10))

    plot = gdf.plot(column='vol_car', 
                    ax=ax,
                    legend=True,
                    legend_kwds={'label': 'Car Volume', 'orientation': 'vertical'},
                    cmap='plasma',
                    linewidth=0.2)

    # Customize the plot
    plt.title(f'Average Car Volume in {city_name.title()}', fontsize=16)
    plt.axis('equal')  # Maintain aspect ratio
    plt.grid(True)
    plt.xlabel('')
    plt.ylabel('')

    # Add north arrow
    ax.annotate('N', xy=(0.02, 0.98), xycoords='axes fraction',
                fontsize=12, ha='center', va='center')
    ax.arrow(0.02, 0.95, 0, 0.02, head_width=0.01, head_length=0.01,
            fc='k', ec='k', transform=ax.transAxes)

    output_plot_path = base_dir / "data" / "scenario_mean" / city_name / f"{city_name}_{road_type}_network_s{scenario_number}_traffic_volume_map.png"
    plt.savefig(output_plot_path, dpi=600, bbox_inches='tight')
    plt.show()

    print(f"Plot saved to: {output_plot_path}")
    print("\nScenario Traffic Volume Statistics:")
    print(gdf['vol_car'].describe()) 


def convert_time_to_seconds(df, column_name):
    """
    Convert time column from string format to seconds (numeric).
    
    Handles both time string formats and already numeric columns gracefully.
    
    Args:
        df (DataFrame): Input dataframe with time column
        column_name (str): Name of the time column to convert
        
    Returns:
        DataFrame: DataFrame with time column converted to seconds (float)
        
    Note:
        Returns unchanged DataFrame if column is already numeric
    """
    if pd.api.types.is_numeric_dtype(df[column_name]):
        return df
    df[column_name] = pd.to_timedelta(df[column_name]).dt.total_seconds()
    return df


def calculate_avg_mode_stats(single_mode_stats_list: list):
    """
    Calculate aggregated trip statistics by transport mode for scenario analysis.
    
    Computes total travel time, total routed distance, and trip counts
    for each transport mode in the scenario simulation.
    
    Args:
        single_mode_stats_list (list): List of DataFrames from scenario simulation runs
                                     Each DataFrame contains trip data with mode, travel_time,
                                     routed_distance, and person_trip_id columns
        
    Returns:
        DataFrame: Aggregated statistics by mode with columns:
                  - mode: Transport mode (car, pt, walk, bike, etc.)
                  - avg_travel_time_seconds: Total travel time for the mode
                  - avg_routed_distance(routed): Total routed distance for the mode
                  - average_trip_count: Total number of trips for the mode
                  
    Note:
        For single scenario runs, "average" refers to the single run totals
        Column names maintain consistency with multi-run analysis patterns
    """
    mode_stats_list = []

    for df in single_mode_stats_list:
        mode_stats = df.groupby('mode').agg({
            'travel_time': 'sum',
            'routed_distance': 'sum',
            'person_trip_id': 'count'
        }).reset_index()
        mode_stats_list.append(mode_stats)

    all_mode_stats = pd.concat(mode_stats_list, ignore_index=True)

    average_mode_stats = all_mode_stats.groupby('mode').agg({
        'travel_time': 'mean',
        'routed_distance': 'mean',
        'person_trip_id': 'mean'
    }).reset_index()

    average_mode_stats.columns = ['mode', 'avg_travel_time_seconds', 'avg_routed_distance(routed)', 'average_trip_count']
    return average_mode_stats


def create_scenario_trips_mean_file(city_name, df_scenario_trips):
    """
    Save aggregated scenario trip statistics as CSV file.
    
    Creates directory structure and saves mode-specific trip statistics
    for scenario comparison and analysis.
    
    Args:
        city_name (str): Name of the city for file naming
        df_scenario_trips (DataFrame): Aggregated trip statistics by mode
        
    Saves:
        CSV file at: data/scenario_mean/<city>/<city>_<road_type>_network_s<scenario>_scenario_average_trips.csv
    """
    result_path_scenario_trips = base_dir / "data" / "scenario_mean" / city_name / f"{city_name}_{road_type}_network_s{scenario_number}_scenario_average_trips.csv"
    result_path_scenario_trips.parent.mkdir(parents=True, exist_ok=True)
    df_scenario_trips.to_csv(result_path_scenario_trips, index=False)


def calculate_edge_metrics(simulation_gdfs, mean_gdf):
    """
    Calculate variability metrics for network edges across scenario runs.
    
    Computes variance, standard deviation, and coefficient of variation
    for traffic volumes on each network link to assess result stability.
    
    Args:
        simulation_gdfs (list): List of GeoDataFrames from scenario simulation runs
        mean_gdf (GeoDataFrame): Mean traffic volume GeoDataFrame to augment
        
    Returns:
        GeoDataFrame: Input mean_gdf with added columns:
                     - variance: Traffic volume variance across runs
                     - cv_percent: Coefficient of variation as percentage
                     - std_dev: Standard deviation of traffic volumes
                     
    Note:
        For single scenario runs, variance and std_dev will be 0, CV will be 0
        Links with zero mean volume get CV of 0 to avoid division by zero
    """
    edge_volumes = {}
    for df in simulation_gdfs:
        for idx, row in df.iterrows():
            link = row['link']
            volume = row['vol_car']
            if link not in edge_volumes:
                edge_volumes[link] = []
            edge_volumes[link].append(volume)
            
    variances = {link: np.var(np.array(volumes)) for link, volumes in edge_volumes.items()}
    cvs = {link: (np.std(np.array(volumes)) / np.mean(np.array(volumes)) * 100) if np.mean(np.array(volumes)) != 0 else 0 for link, volumes in edge_volumes.items()}
    std_devs = {link: np.std(np.array(volumes)) for link, volumes in edge_volumes.items()}
    
    mean_gdf['variance'] = mean_gdf['link'].map(variances)
    mean_gdf['cv_percent'] = mean_gdf['link'].map(cvs)
    mean_gdf['std_dev'] = mean_gdf['link'].map(std_devs)
    return mean_gdf


def print_edge_metrics(mean_gdf):
    """
    Print comprehensive statistics about scenario traffic volume characteristics.
    
    Displays overall network statistics and breakdown by highway type
    for mean volumes, variance, coefficient of variation, and standard deviation.
    
    Args:
        mean_gdf (GeoDataFrame): Scenario network data with calculated metrics
        
    Prints:
        - Overall scenario network statistics (mean volume, observations, variance, CV, std dev)
        - Same statistics broken down by highway type (trunk, primary, secondary, etc.)
        
    Note:
        For single scenario runs, variance and std_dev will be 0
        Assumes highway column exists and contains standard OSM highway types
    """
    mean_car_volume = mean_gdf['vol_car'].mean()
    print(f"Mean Car Volume over all edges: {mean_car_volume:.2f}")
    
    num_observations = len(mean_gdf)
    print(f"Number of observations (links): {num_observations}")
    
    mean_variance = mean_gdf['variance'].mean()
    print(f"Mean Variance over all edges: {mean_variance:.2f}")

    mean_cv_percent = mean_gdf['cv_percent'].mean()
    print(f"Mean Coefficient of Variation (CV) over all edges: {mean_cv_percent:.2f}%")
    
    mean_std_dev = mean_gdf['std_dev'].mean()
    print(f"Mean Standard Deviation over all edges: {mean_std_dev:.2f}")
    
    print("\nMetrics by highway type:")
    highway_types = ['trunk', 'primary', 'secondary', 'tertiary', 'residential', 'living_street']
    for highway in highway_types:
        highway_gdf = mean_gdf[mean_gdf['highway'] == highway]
        if len(highway_gdf) > 0:
            highway_mean_car_volume = highway_gdf['vol_car'].mean()
            print(f"\nMean Car Volume for {highway} roads: {highway_mean_car_volume:.2f}")
            
            num_highway_observations = len(highway_gdf)
            print(f"Number of observations for {highway} roads: {num_highway_observations}")
            
            highway_mean_variance = highway_gdf['variance'].mean()
            print(f"Mean Variance for {highway} roads: {highway_mean_variance:.2f}")
            
            highway_mean_cv = highway_gdf['cv_percent'].mean()
            print(f"Mean Coefficient of Variation (CV) for {highway} roads: {highway_mean_cv:.2f}%")
            
            highway_mean_std_dev = highway_gdf['std_dev'].mean()
            print(f"Mean Standard Deviation for {highway} roads: {highway_mean_std_dev:.2f}")
   

def plot_edge_metrics(gdf_scenario_mean):
    """
    Create scatter plot showing traffic volume characteristics for a sample link.
    
    Visualizes traffic volumes for a single trunk road link to demonstrate
    scenario results and any variability across runs.
    
    Args:
        gdf_scenario_mean (GeoDataFrame): Scenario mean network data
        
    Displays:
        Scatter plot with:
        - Blue dots: Volume values for each run (single point for single scenario)
        - Red dashed line: Mean volume
        - Green dotted line: Perfect regression reference
        
    Prints:
        Statistical summary for the analyzed link including mean, run count, std dev
        
    Note:
        Uses the 2nd trunk link found in the dataset as example
        For single scenario runs, plot will show single data point
    """
    trunk_links = gdf_scenario_mean[gdf_scenario_mean['highway'] == 'trunk']['link']
    if len(trunk_links) < 2:
        print("Not enough trunk links for plotting")
        return
        
    trunk_link = trunk_links.iloc[1] #might need to change index if that LINK is problematic
    true_mean = gdf_scenario_mean[gdf_scenario_mean['link'] == trunk_link]['vol_car'].iloc[0]

    simulated_volumes = []
    for df in scenario_output_links_gdfs:
        if trunk_link in df['link'].values:
            volume = df[df['link'] == trunk_link]['vol_car'].iloc[0]
            simulated_volumes.append(volume)

    run_numbers = range(1, len(simulated_volumes) + 1)

    plt.figure(figsize=(10, 6))
    plt.scatter(run_numbers, simulated_volumes, color='blue', label='Scenario runs')
    plt.axhline(y=true_mean, color='r', linestyle='--', label='Mean volume')
    plt.plot(run_numbers, simulated_volumes, color='green', linestyle=':', label='Perfect regression')

    plt.xlabel('Simulation Run Number')
    plt.ylabel('Car Volume')
    plt.title(f'Car Volumes per Simulation Run for Trunk Link {trunk_link}\nTrue Mean: {true_mean:.2f}')
    plt.legend()
    plt.grid(True)
    plt.show()

    # Print some statistics
    print(f"True mean: {true_mean:.2f}")
    print(f"Number of simulation runs: {len(simulated_volumes)}")
    print(f"Standard deviation: {np.std(simulated_volumes):.2f}")
    

def extend_geodataframe(gdf_base, gdf_to_extend, column_to_extend: str, new_column_name: str):
    """
    Extend a GeoDataFrame by adding a column from another GeoDataFrame.
    
    Copies a specified column from one GeoDataFrame to another with a new name,
    useful for combining baseline and scenario data structures.
    
    Args:
        gdf_base (GeoDataFrame): Source GeoDataFrame containing the column to copy
        gdf_to_extend (GeoDataFrame): Target GeoDataFrame to receive the new column
        column_to_extend (str): Name of column to copy from source
        new_column_name (str): Name for the new column in target GeoDataFrame
    
    Returns:
        GeoDataFrame: Copy of target GeoDataFrame with added column from source
        
    Raises:
        ValueError: If specified column doesn't exist in source GeoDataFrame
        
    Note:
        Assumes both GeoDataFrames have the same row ordering and structure
    """
    if column_to_extend not in gdf_base.columns:
        raise ValueError(f"Column '{column_to_extend}' does not exist in the base GeoDataFrame")
    
    extended_gdf = gdf_to_extend.copy()
    extended_gdf[new_column_name] = gdf_base[column_to_extend]
    return extended_gdf


def remove_columns(gdf_with_correct_columns, gdf_to_be_adapted):
    """
    Remove columns from GeoDataFrame to match another's column structure.
    
    Filters columns to ensure consistent structure between GeoDataFrames
    for proper comparison and analysis operations.
    
    Args:
        gdf_with_correct_columns (GeoDataFrame): Template GeoDataFrame with desired columns
        gdf_to_be_adapted (GeoDataFrame): GeoDataFrame to filter columns from
    
    Returns:
        GeoDataFrame: Filtered GeoDataFrame containing only columns present in template
        
    Note:
        Useful for ensuring baseline and scenario data have matching structures
    """
    columns_to_keep = gdf_with_correct_columns.columns
    gdf1_filtered = gdf_to_be_adapted[columns_to_keep]
    return gdf1_filtered


def compute_difference_geodataframe(gdf_to_substract_from, gdf_to_substract, column_name):
    """
    Compute difference metrics between scenario and baseline GeoDataFrames.
    
    Calculates absolute and percentage differences for traffic volumes,
    providing comprehensive comparison between intervention and baseline conditions.
    
    Args:
        gdf_to_substract_from (GeoDataFrame): Scenario data (values to subtract from)
        gdf_to_substract (GeoDataFrame): Baseline data (values to subtract)
        column_name (str): Column name for difference computation (typically 'vol_car')
    
    Returns:
        GeoDataFrame: Copy of scenario GeoDataFrame with added difference columns:
                     - <column_name>: Absolute difference (scenario - baseline)
                     - <column_name>_percentage_difference: Percentage change
                     - <column_name>_clipped_percentage_difference: Percentage change clipped to ±100%
                     
    Raises:
        ValueError: If GeoDataFrames have different shapes, indices, or geometries
        
    Note:
        Handles division by zero gracefully, replacing infinities with NaN
        Clips percentage differences to ±100% for better visualization
    """
    if gdf_to_substract_from.shape != gdf_to_substract.shape:
        raise ValueError("GeoDataFrames must have the same shape")

    if not gdf_to_substract_from.index.equals(gdf_to_substract.index):
        raise ValueError("GeoDataFrames must have the same indices")
    
    if not gdf_to_substract_from.geometry.equals(gdf_to_substract.geometry):
        raise ValueError("GeoDataFrames must have the same geometries")
    
    difference_gdf = gdf_to_substract_from.copy()

    values_from = pd.to_numeric(gdf_to_substract_from[column_name], errors='coerce')
    values_to_substract = pd.to_numeric(gdf_to_substract[column_name], errors='coerce')

    difference_gdf[column_name] = values_from - values_to_substract
    
    difference_gdf[column_name + "_percentage_difference"] = (
        (difference_gdf[column_name] / values_to_substract * 100)
        .replace([np.inf, -np.inf], np.nan)
    )
    
    difference_gdf[column_name + "_clipped_percentage_difference"] = np.clip(
        difference_gdf[column_name + "_percentage_difference"], 
        -100, 
        100
    )
 
    return difference_gdf


if __name__ == "__main__":
    """
    Main execution block for scenario analysis and baseline comparison.
    
    Processes scenario simulation results and compares them against baseline conditions:
    1. Loads scenario simulation output data
    2. Computes scenario statistics and metrics
    3. Loads corresponding baseline data
    4. Performs difference analysis between scenario and baseline
    5. Creates visualizations and saves processed results
    6. Prints comprehensive statistical summaries
    
    Configuration is controlled by global variables at the top of the file.
    
    Outputs:
        - Scenario mean network files and visualizations
        - Difference analysis files showing intervention impacts
        - Trip statistics for scenario conditions
        - Statistical summaries printed to console
    """
    # Load scenario data
    random_seed_2_df_scenario_output_links = create_dic_seed_to_output_links(subdir=scenario_subdir_path)
    random_seed_2_df_scenario_trips = create_dic_seed_to_eqasim_trips_given_output_trips(subdir=scenario_subdir_path)

    scenario_output_links_gdfs = list(random_seed_2_df_scenario_output_links.values())

    # Process scenario network data
    gdf_scenario_mean = compute_average_or_median_geodataframe(geodataframes=scenario_output_links_gdfs, column_name="vol_car", is_mean=True)
    gdf_scenario_mean = gdf_scenario_mean.rename(columns={"osm:way:highway": "highway"})
    
    # Load baseline data for comparison
    gdf_basecase_mean = gpd.read_file(base_dir / "data" / "basecases_mean" / city_name / f"{city_name}_basecase_average_output_links.geojson")
    
    # Align data structures for comparison
    gdf_comparison_mean_extended = extend_geodataframe(gdf_base=gdf_basecase_mean, gdf_to_extend=gdf_scenario_mean, column_to_extend='highway', new_column_name='highway')
    gdf_basecase_without_unnecessary_columns = remove_columns(gdf_with_correct_columns=gdf_comparison_mean_extended, gdf_to_be_adapted=gdf_basecase_mean)
    
    # Compute difference metrics
    gdf_basecase_difference = compute_difference_geodataframe(gdf_to_substract_from=gdf_comparison_mean_extended, gdf_to_substract=gdf_basecase_without_unnecessary_columns, column_name='vol_car')
    
    # Save results
    create_scenario_output_links_mean_file(city_name=city_name, gdf_scenario_mean=gdf_comparison_mean_extended, road_type=road_type)
    create_difference_output_links_mean_file(city_name=city_name, gdf_difference_mean=gdf_basecase_difference, road_type=road_type)

    # Generate visualizations and analysis
    #plot_scenario_mean_file(city_name=city_name, road_type=road_type)
    #gdf_scenario_mean = calculate_edge_metrics(simulation_gdfs=scenario_output_links_gdfs, mean_gdf=gdf_scenario_mean)
    #print_edge_metrics(gdf_scenario_mean)
    #plot_edge_metrics(gdf_scenario_mean)

    # Process trip data
    #scenario_trips_dfs = list(random_seed_2_df_scenario_trips.values())
    #df_average_mode_stats = calculate_avg_mode_stats(scenario_trips_dfs)
    #create_scenario_trips_mean_file(city_name=city_name, df_scenario_trips=df_average_mode_stats)

    #print(f"\nScenario analysis complete for {city_name} {road_type} network scenario {scenario_number}")
    #print(f"Results saved to data/scenario_mean/{city_name}/ and data/difference_mean/{city_name}/")
