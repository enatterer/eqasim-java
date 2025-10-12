"""
Basecase Analysis and Averaging Module for MATSim Simulation Results

This module processes multiple MATSim simulation runs to compute statistical measures
and create averaged baseline datasets for network analysis. It analyzes traffic volumes,
trip statistics, and variability metrics across different simulation seeds.

Key Operations:
    1. Load simulation output files from multiple random seeds
    2. Compute mean/median traffic volumes across simulation runs
    3. Calculate variability metrics (variance, CV, standard deviation)
    4. Generate averaged trip statistics by transport mode
    5. Create visualizations and save processed baseline data

Output Files:
    - <city>_basecase_average_output_links.geojson: Averaged network with traffic volumes
    - <city>_basecase_average_trips.csv: Mode-specific trip statistics
    - <city>_traffic_volume_map.png: Traffic volume visualization

Usage:
    python3 create_basecase_means.py

    # Processes all cities defined in city_name list (in the main function)
    # Reads from: data/simulation_output/basecases_new/<city>/
    # Outputs to: data/basecases_mean/<city>/

Requirements:
    - MATSim simulation output files (output_links.csv.gz, eqasim_trips.csv)
    - Multiple simulation runs with different random seeds
    - Consistent network structure across all simulation runs
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


def create_dic_seed_to_output_links(subdir):
    """
    Load output_links files from multiple simulation seeds into a dictionary.
    
    Reads compressed CSV files containing network link data from different
    simulation runs and converts them to GeoDataFrames.
    
    Args:
        subdir (Path): Directory containing subdirectories for each simulation seed
        
    Returns:
        dict: Seed number to GeoDataFrame mapping
              Keys: str (seed numbers extracted from directory names)
              Values: GeoDataFrame with network links and traffic volumes
              
    Note:
        Expects subdirectories named with pattern ending in "_<seed_number>"
        Each subdirectory should contain "output_links.csv.gz" file
    """
    result_dic = {}
    for subdir in basecase_subdir_path.iterdir():
        subdir_name = subdir.name
        seed_number = subdir_name.split("_")[-1]
        output_links_path = subdir / 'output_links.csv.gz'
        if os.path.exists(output_links_path):
            # Read as DataFrame first
            df_output_links = pd.read_csv(output_links_path, delimiter=';', low_memory=False)
            # Convert to GeoDataFrame using the geometry column
            if 'geometry' in df_output_links.columns:
                df_output_links['geometry'] = gpd.GeoSeries.from_wkt(df_output_links['geometry'])
                gdf_output_links = gpd.GeoDataFrame(df_output_links, geometry='geometry')
                result_dic[seed_number] = gdf_output_links
    return result_dic


def create_dic_seed_to_eqasim_trips_given_output_trips(subdir):
    """
    Load eqasim_trips files from multiple simulation seeds into a dictionary.
    
    Reads trip data files containing detailed trip information from different
    simulation runs for subsequent statistical analysis.
    
    Args:
        subdir (Path): Directory containing subdirectories for each simulation seed
        
    Returns:
        dict: Seed number to DataFrame mapping
              Keys: str (seed numbers extracted from directory names)  
              Values: DataFrame with trip data (travel times, distances, modes)
              
    Note:
        Expects subdirectories named with pattern ending in "_<seed_number>"
        Each subdirectory should contain "eqasim_trips.csv" file
    """
    result_dic = {}
    for subdir in basecase_subdir_path.iterdir():
        subdir_name = subdir.name
        seed_number = subdir_name.split("_")[-1]
        output_trips_path = subdir / 'eqasim_trips.csv'
        if os.path.exists(output_trips_path):
            df_output_trips = pd.read_csv(output_trips_path, delimiter=';', low_memory=False)
            result_dic[seed_number] = df_output_trips
    return result_dic
    

def compute_average_or_median_geodataframe(geodataframes, column_name, is_mean: bool = True):
    """
    Compute statistical measures across multiple GeoDataFrames for a specified column.
    
    Calculates either mean or median values for a numeric column across multiple
    simulation runs, maintaining the spatial structure of the original data.
    
    Args:
        geodataframes (list): List of GeoDataFrames with identical structure
        column_name (str): Column name for statistical computation
        is_mean (bool, optional): If True computes mean, else median. Defaults to True
        
    Returns:
        GeoDataFrame: Copy of first input GeoDataFrame with updated statistical values
                     in the specified column, all other columns and geometry preserved
                     
    Raises:
        IndexError: If geodataframes list is empty
        KeyError: If column_name doesn't exist in the GeoDataFrames
        
    Note:
        All input GeoDataFrames must have identical structure and row ordering
    """
    # Create a copy of the first GeoDataFrame to use as the base
    average_gdf = geodataframes[0].copy()
    
    # Extract the specified column values from all GeoDataFrames
    column_values = np.array([gdf[column_name].values for gdf in geodataframes])
    
    if (is_mean):
        # Calculate the average values for the specified column
        column_average = np.mean(column_values, axis=0)
    else:
        column_average = np.median(column_values, axis=0)

    # Assign the average values to the new GeoDataFrame
    average_gdf[column_name] = column_average
    
    return average_gdf    


def create_basecase_output_links_mean_file(city_name, gdf_basecase_mean):
    """
    Save averaged network data as GeoJSON file.
    
    Creates directory structure and saves the averaged network with traffic
    volumes and statistical measures for further analysis.
    
    Args:
        city_name (str): Name of the city for file naming
        gdf_basecase_mean (GeoDataFrame): Averaged network data to save
        
    Saves:
        GeoJSON file at: data/basecases_mean/<city_name>/<city_name>_basecase_average_output_links.geojson
    """
    result_path_basecase_mean = base_dir / "data" / "basecases_mean" / city_name / f"{city_name}_basecase_average_output_links.geojson"
    # Create the directory structure if it doesn't exist
    result_path_basecase_mean.parent.mkdir(parents=True, exist_ok=True)
    gdf_basecase_mean.to_file(result_path_basecase_mean, driver='GeoJSON')


def plot_basecase_mean_file(city_name):
    """
    Create and save traffic volume visualization map.
    
    Generates a high-resolution map showing car traffic volumes across the
    network using color coding, with north arrow and basic statistics.
    
    Args:
        city_name (str): Name of the city for plot title and file naming
        
    Saves:
        PNG file at: data/basecases_mean/<city_name>/<city_name>_traffic_volume_map.png
        
    Prints:
        File save location and traffic volume statistics summary
        
    Note:
        Reads GeoJSON file created by create_basecase_output_links_mean_file()
    """
    # Set up the paths
    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    geojson_path = base_dir / "data" / "basecases_mean" / city_name / f"{city_name}_basecase_average_output_links.geojson"

    # Read the GeoJSON file
    gdf = gpd.read_file(geojson_path)

    # Create a figure with a specific size
    fig, ax = plt.subplots(figsize=(15, 10))

    # Plot the road network
    # Color the roads based on car volume, using a color map
    plot = gdf.plot(column='vol_car', 
                    ax=ax,
                    legend=True,
                    legend_kwds={'label': 'Car Volume',
                                'orientation': 'vertical'},
                    cmap='plasma',  # Yellow to Red colormap
                    linewidth=0.2,aspect=1)

    # Customize the plot
    plt.title(f'Average Car Volume in {city_name.title()}', fontsize=16)
    plt.axis('equal')  # Maintain aspect ratio
    plt.grid(True)

    # Remove axis labels as they're not typically needed for maps
    plt.xlabel('')
    plt.ylabel('')

    # Add a simple north arrow
    ax.annotate('N', xy=(0.02, 0.98), xycoords='axes fraction',
                fontsize=12, ha='center', va='center')
    ax.arrow(0.02, 0.95, 0, 0.02, head_width=0.01, head_length=0.01,
            fc='k', ec='k', transform=ax.transAxes)

    # Save the plot
    output_plot_path = base_dir / "data" / "basecases_mean" / city_name / f"{city_name}_traffic_volume_map.png"
    plt.savefig(output_plot_path, dpi=600, bbox_inches='tight')
    plt.show()

    print(f"Plot saved to: {output_plot_path}")

    # Print some basic statistics about the car volumes
    print("\nTraffic Volume Statistics:")
    print(gdf['vol_car'].describe()) 


def convert_time_to_seconds(df, column_name):
    """
    Convert time column from string format to seconds (numeric).
    
    Handles both time string formats and already numeric columns.
    
    Args:
        df (DataFrame): Input dataframe with time column
        column_name (str): Name of the time column to convert
        
    Returns:
        DataFrame: DataFrame with time column converted to seconds (float)
        
    Note:
        Returns unchanged DataFrame if column is already numeric
    """
    # If the column is already numeric (float), return as is
    if pd.api.types.is_numeric_dtype(df[column_name]):
        return df
    # Otherwise convert from time string to seconds
    df[column_name] = pd.to_timedelta(df[column_name]).dt.total_seconds()
    return df


def calculate_avg_mode_stats(single_mode_stats_list: list):
    """
    Calculate averaged trip statistics across simulation runs by transport mode.
    
    Aggregates travel time, trip count, and routed distance statistics
    for each transport mode across multiple simulation seeds.
    
    Args:
        single_mode_stats_list (list): List of DataFrames from different simulation runs
                                     Each DataFrame contains trip data with mode, travel_time,
                                     and routed_distance columns
        
    Returns:
        DataFrame: Averaged statistics by mode with columns:
                  - mode: Transport mode (car, pt, walk, bike, etc.)
                  - avg_total_travel_time: Mean travel time across all runs
                  - avg_total_routed_distance: Mean routed distance across all runs  
                  - avg_trip_count: Mean number of trips across all runs
                  
    Note:
        Assumes consistent mode categories across all simulation runs
    """
    mode_stats_list = []
    for df in single_mode_stats_list:
        mode_stats = df.groupby('mode').agg({
            'travel_time': ['mean', 'count'],
            'routed_distance': 'mean'
        }).reset_index()
        mode_stats.columns = ['mode', 'avg_travel_time', 'trip_count', 'avg_routed_distance']
        mode_stats_list.append(mode_stats)
    all_mode_stats = pd.concat(mode_stats_list, ignore_index=True)

    # Calculate the average across all seeds
    average_mode_stats = all_mode_stats.groupby('mode').agg({
        'avg_travel_time': 'mean',
        'avg_routed_distance': 'mean',
        'trip_count': 'mean'
    }).reset_index()
    average_mode_stats.columns = ['mode', 'avg_total_travel_time', 'avg_total_routed_distance', 'avg_trip_count']
    df_average_mode_stats = pd.DataFrame(average_mode_stats)
    return df_average_mode_stats


def create_basecase_trips_mean_file(city_name, df_basecase_trips):
    """
    Save averaged trip statistics as CSV file.
    
    Creates directory structure and saves mode-specific trip statistics
    for baseline comparison in further analysis.
    
    Args:
        city_name (str): Name of the city for file naming
        df_basecase_trips (DataFrame): Averaged trip statistics by mode
        
    Saves:
        CSV file at: data/basecases_mean/<city_name>/<city_name>_basecase_average_trips.csv
    """
    result_path_basecase_trips = base_dir / "data" / "basecases_mean" / city_name / f"{city_name}_basecase_average_trips.csv"
    # Create the directory structure if it doesn't exist
    result_path_basecase_trips.parent.mkdir(parents=True, exist_ok=True)
    df_basecase_trips.to_csv(result_path_basecase_trips, index=False)


def calculate_edge_metrics(simulation_gdfs, mean_gdf):
    """
    Calculate variability metrics for network edges across simulation runs.
    
    Computes variance, standard deviation, and coefficient of variation
    for traffic volumes on each network link to assess result stability.
    
    Args:
        simulation_gdfs (list): List of GeoDataFrames from different simulation runs
        mean_gdf (GeoDataFrame): Mean traffic volume GeoDataFrame to augment
        
    Returns:
        GeoDataFrame: Input mean_gdf with added columns:
                     - variance: Traffic volume variance across runs
                     - cv_percent: Coefficient of variation as percentage
                     - std_dev: Standard deviation of traffic volumes
                     
    Note:
        Links with zero mean volume get CV of 0 to avoid division by zero
    """
    # Concatenate all simulation DataFrames, adding a simulation id if needed
    all_dfs = pd.concat(simulation_gdfs, ignore_index=True)
    
    # Group by 'link' and aggregate
    grouped = all_dfs.groupby('link')['vol_car']
    variances = grouped.var().to_dict()
    std_devs = grouped.std().to_dict()
    means = grouped.mean().to_dict()
    
    # Coefficient of Variation (CV) as percentage
    cvs = {link: (std_devs[link] / means[link] * 100) if means[link] != 0 else 0 for link in means}
    
    # Map results back to mean_gdf
    mean_gdf['variance'] = mean_gdf['link'].map(variances)
    mean_gdf['cv_percent'] = mean_gdf['link'].map(cvs)
    mean_gdf['std_dev'] = mean_gdf['link'].map(std_devs)
    return mean_gdf


def print_edge_metrics(mean_gdf):
    """
    Print comprehensive statistics about traffic volume variability.
    
    Displays overall network statistics and breakdown by highway type
    for mean volumes, variance, coefficient of variation, and standard deviation.
    
    Args:
        mean_gdf (GeoDataFrame): Network data with calculated variability metrics
        
    Prints:
        - Overall network statistics (mean volume, observations, variance, CV, std dev)
        - Same statistics broken down by highway type (trunk, primary, secondary, etc.)
        
    Note:
        Assumes highway column exists and contains standard OSM highway types
    """
    # Compute and print the mean car volume over all edges
    mean_car_volume = mean_gdf['vol_car'].mean()
    print(f"Mean Car Volume over all edges: {mean_car_volume:.2f}")
    
    num_observations = len(mean_gdf)
    print(f"Number of observations (links): {num_observations}")
    
    # Compute and print the mean variance over all edges
    mean_variance = mean_gdf['variance'].mean()
    print(f"Mean Variance over all edges: {mean_variance:.2f}")

    # Compute and print the mean Coefficient of Variation (CV) over all edges
    mean_cv_percent = mean_gdf['cv_percent'].mean()
    print(f"Mean Coefficient of Variation (CV) over all edges: {mean_cv_percent:.2f}%")
    
    # Compute and print the mean of the standard deviations over all edges
    mean_std_dev = mean_gdf['std_dev'].mean()
    print(f"Mean Standard Deviation over all edges: {mean_std_dev:.2f}")
    
    print("\nMetrics by highway type:")
    # Compute and print metrics by highway type
    highway_types = ['trunk', 'primary', 'secondary', 'tertiary', 'residential', 'living_street']
    for highway in highway_types:
        highway_gdf = mean_gdf[mean_gdf['highway'] == highway]
        
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
   

def plot_edge_metrics(gdf_basecase_mean):
    """
    Create scatter plot showing traffic volume variability for a sample link.
    
    Visualizes traffic volumes across simulation runs for a single trunk road
    link to demonstrate result variability and regression patterns.
    
    Args:
        gdf_basecase_mean (GeoDataFrame): Mean network data with calculated metrics
        
    Displays:
        Scatter plot with:
        - Blue dots: Simulated volumes for each run
        - Red dashed line: True mean volume
        - Green dotted line: Perfect regression line
        
    Prints:
        Statistical summary for the analyzed link including mean, run count, std dev
        
    Note:
        Uses the 3rd trunk link found in the dataset as example
        Requires global variable basecase_output_links_gdfs to be defined
    """
    # Get one trunk link
    trunk_link = gdf_basecase_mean[gdf_basecase_mean['highway'] == 'trunk']['link'].iloc[2]

    # Get the true mean volume from gdf_basecase_mean
    true_mean = gdf_basecase_mean[gdf_basecase_mean['link'] == trunk_link]['vol_car'].iloc[0]

    # Get all simulated volumes for this link from different runs
    simulated_volumes = []
    for df in basecase_output_links_gdfs:
        if trunk_link in df['link'].values:
            volume = df[df['link'] == trunk_link]['vol_car'].iloc[0]
            simulated_volumes.append(volume)

    # Create x-axis (simulation run numbers)
    run_numbers = range(1, len(simulated_volumes) + 1)

    # Create plot
    plt.figure(figsize=(10, 6))

    # Plot simulated volumes
    plt.scatter(run_numbers, simulated_volumes, color='blue', label='Simulation runs')

    # Plot mean line
    plt.axhline(y=true_mean, color='r', linestyle='--', label='True mean')

    # Plot "perfect" regression line (y=x scaled to our data range)
    # This would represent perfect correlation between runs
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


if __name__ == "__main__":
    """
    Main execution block for processing all Bavarian cities.
    
    Processes simulation results for all 16 major Bavarian cities to create
    baseline averages and statistical measures for network analysis.
    
    For each city:
    1. Loads simulation output from multiple seeds
    2. Computes averaged traffic volumes and trip statistics  
    3. Calculates variability metrics
    4. Creates visualizations and saves processed data
    5. Prints summary statistics
    
    Cities processed: rosenheim, muenchen, schweinfurt, bamberg, aschaffenburg,
                     erlangen, kempten, fuerth, landshut, bayreuth, ingolstadt,
                     regensburg, wuerzburg, augsburg, nuernberg, neuulm
    """
    city_name = ["rosenheim","muenchen","schweinfurt","bamberg","aschaffenburg","erlangen","kempten","fuerth","landshut","bayreuth","ingolstadt","regensburg","wuerzburg","augsburg","nuernberg","neuulm"]
    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    for city in city_name:
        basecase_subdir_path = base_dir / "data" / "simulation_output" / "basecases_new" / city
        result_path_basecase_mean = base_dir / "data" / "basecases_mean" / city
        result_path_basecase_trips = base_dir / "data" / "basecases_mean" / city / f"{city}_basecase_average_trips.csv"

        random_seed_to_df_basecase_output_links = create_dic_seed_to_output_links(subdir=basecase_subdir_path)
        random_seed_to_df_basecase_trips = create_dic_seed_to_eqasim_trips_given_output_trips(subdir=basecase_subdir_path)

        basecase_output_links_gdfs = list(random_seed_to_df_basecase_output_links.values())

        gdf_basecase_mean = compute_average_or_median_geodataframe(geodataframes=basecase_output_links_gdfs, column_name="vol_car", is_mean=True)
        gdf_basecase_mean = gdf_basecase_mean.rename(columns={"osm:way:highway": "highway"})
        create_basecase_output_links_mean_file(city_name=city,gdf_basecase_mean=gdf_basecase_mean)
        plot_basecase_mean_file(city_name=city)
        gdf_basecase_mean = calculate_edge_metrics(simulation_gdfs=basecase_output_links_gdfs, mean_gdf=gdf_basecase_mean)
        print_edge_metrics(gdf_basecase_mean)
        #plot_edge_metrics(gdf_basecase_mean)

        basecase_trips_dfs = list(random_seed_to_df_basecase_trips.values())
        df_average_mode_stats = calculate_avg_mode_stats(basecase_trips_dfs)
        create_basecase_trips_mean_file(city_name=city,df_basecase_trips=df_average_mode_stats)










