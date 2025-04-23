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


city_name = "augsburg"

base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
scenario_subdir_path = base_dir / "data" / "simulation_output" / "scenarios" / city_name / f"{city_name}_seed_6_capfactor_0.5"
result_path_scenario_mean = base_dir / "data" / "scenario_mean"
result_path_difference = base_dir / "data" / "difference_mean"

def create_dic_seed_to_output_links(subdir):
    result_dic = {}
    # We're looking for a specific file, not iterating through subdirs
    output_links_path = scenario_subdir_path / 'output_links.csv.gz'
    if output_links_path.exists():
        # Read as DataFrame first
        df_output_links = pd.read_csv(output_links_path, 
                                    delimiter=';',
                                    low_memory=False)
        # Convert to GeoDataFrame using the geometry column
        if 'geometry' in df_output_links.columns:
            df_output_links['geometry'] = gpd.GeoSeries.from_wkt(df_output_links['geometry'])
            gdf_output_links = gpd.GeoDataFrame(df_output_links, geometry='geometry')
            result_dic['1'] = gdf_output_links  # Using '1' as key since it's seed 1
    return result_dic

def create_dic_seed_to_eqasim_trips_given_output_trips(subdir):
    result_dic = {}
    eqasim_trips_path = scenario_subdir_path / 'eqasim_trips.csv'
    if eqasim_trips_path.exists():
        df_eqasim_trips = pd.read_csv(eqasim_trips_path, delimiter=';')
        result_dic['1'] = df_eqasim_trips
    return result_dic
    
def compute_average_or_median_geodataframe(geodataframes, column_name, is_mean: bool = True):
    """
    Compute the average GeoDataFrame from a list of GeoDataFrames for a specified column.
    
    Parameters:
    geodataframes (list of GeoDataFrames): List containing GeoDataFrames
    column_name (str): The column name for which to compute the average
    
    Returns:
    GeoDataFrame: A new GeoDataFrame with the average values for the specified column
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

def create_scenario_output_links_mean_file(city_name, gdf_scenario_mean):
    result_path_scenario_mean = base_dir / "data" / "scenario_mean" / city_name / f"{city_name}_secondary_scenario_average_output_links.geojson"
    # Create the directory structure if it doesn't exist
    result_path_scenario_mean.parent.mkdir(parents=True, exist_ok=True)
    gdf_scenario_mean.to_file(result_path_scenario_mean, driver='GeoJSON')

def create_difference_output_links_mean_file(city_name, gdf_difference_mean):
    result_path_difference = base_dir / "data" / "difference_mean" / city_name / f"{city_name}_secondary_difference_average_output_links.geojson"
    # Create the directory structure if it doesn't exist
    result_path_difference.parent.mkdir(parents=True, exist_ok=True)
    gdf_difference_mean.to_file(result_path_difference, driver='GeoJSON')

def plot_scenario_mean_file(city_name,): 
    # Set up the paths
    geojson_path = base_dir / "data" / "scenario_mean" / city_name / f"{city_name}_secondary_scenario_average_output_links.geojson"

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
                    linewidth=0.2)

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
    output_plot_path = base_dir / "data" / "scenario_mean" / city_name / f"{city_name}_secondary_traffic_volume_map.png"
    plt.savefig(output_plot_path, dpi=600, bbox_inches='tight')
    plt.show()

    print(f"Plot saved to: {output_plot_path}")

    # Print some basic statistics about the car volumes
    print("\nTraffic Volume Statistics:")
    print(gdf['vol_car'].describe()) 

def convert_time_to_seconds(df, column_name):
    # If the column is already numeric (float), return as is
    if pd.api.types.is_numeric_dtype(df[column_name]):
        return df
    # Otherwise convert from time string to seconds
    df[column_name] = pd.to_timedelta(df[column_name]).dt.total_seconds()
    return df

# Calculate average travel time, routed distance, and trip count per mode across all seeds
def calculate_avg_mode_stats(single_mode_stats_list: list):
    mode_stats_list = []

    for df in single_mode_stats_list:
        # Aggregate travel time (sum), traveled distance (sum), and trip count by main mode
        mode_stats = df.groupby('mode').agg({
            'travel_time': 'sum',  # Sum all travel times per mode
            'routed_distance': 'sum',  # Sum all distances per mode
            'person_trip_id': 'count'  # Count trips
        }).reset_index()
        mode_stats_list.append(mode_stats)

    # Concatenate all mode_stats dataframes
    all_mode_stats = pd.concat(mode_stats_list, ignore_index=True)

    # Calculate the average of the sums across all seeds
    average_mode_stats = all_mode_stats.groupby('mode').agg({
        'travel_time': 'mean',  # Average the summed travel times across seeds
        'routed_distance': 'mean',  # Average the summed distances across seeds
        'person_trip_id': 'mean'  # Average the trip counts across seeds
    }).reset_index()

    # Rename columns for clarity
    average_mode_stats.columns = ['mode', 'avg_travel_time_seconds', 'avg_routed_distance(routed)', 'average_trip_count']
    
    return average_mode_stats

def create_scenario_trips_mean_file(city_name,df_scenario_trips):
    result_path_scenario_trips = base_dir / "data" / "scenario_mean" / city_name / f"{city_name}_scenario_average_trips.csv"
    # Create the directory structure if it doesn't exist
    result_path_scenario_trips.parent.mkdir(parents=True, exist_ok=True)
    df_scenario_trips.to_csv(result_path_scenario_trips, index=False)

def calculate_edge_metrics(simulation_gdfs, mean_gdf):
    edge_volumes = {}
    # Collect volumes for each edge across all simulations
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
    
    # Add metrics to the mean_gdf
    mean_gdf['variance'] = mean_gdf['link'].map(variances)
    mean_gdf['cv_percent'] = mean_gdf['link'].map(cvs)  # Coefficient of Variation as percentage
    mean_gdf['std_dev'] = mean_gdf['link'].map(std_devs)
    return mean_gdf

def print_edge_metrics(mean_gdf):
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
   
def plot_edge_metrics(gdf_scenario_mean):
    # Get one trunk link
    trunk_link = gdf_scenario_mean[gdf_scenario_mean['highway'] == 'trunk']['link'].iloc[1]

    # Get the true mean volume from gdf_basecase_mean
    true_mean = gdf_scenario_mean[gdf_scenario_mean['link'] == trunk_link]['vol_car'].iloc[0]

    # Get all simulated volumes for this link from different runs
    simulated_volumes = []
    for df in scenario_output_links_gdfs:
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
    
def extend_geodataframe(gdf_base, gdf_to_extend, column_to_extend: str, new_column_name: str):
    """
    Extend a GeoDataFrame by adding a column from another GeoDataFrame.
    
    Parameters:
    gdf_base (GeoDataFrame): The GeoDataFrame containing the column to add
    gdf_to_extend (GeoDataFrame): The GeoDataFrame to be extended
    column_name (str): The column name to add to gdf_to_extend
    new_column_name (str): The new column name to use in gdf_to_extend

    
    Returns:
    GeoDataFrame: A new GeoDataFrame with the column added
    """
    # Ensure the column exists in the base GeoDataFrame
    if column_to_extend not in gdf_base.columns:
        raise ValueError(f"Column '{column_to_extend}' does not exist in the base GeoDataFrame")
    
    # Create a copy of the GeoDataFrame to be extended
    extended_gdf = gdf_to_extend.copy()
    
    # Add the column from the base GeoDataFrame
    extended_gdf[new_column_name] = gdf_base[column_to_extend]
    
    return extended_gdf

def remove_columns(gdf_with_correct_columns, gdf_to_be_adapted):
    """
    Remove columns from gdf1 that are not present in gdf2.
    
    Parameters:
    gdf1 (GeoDataFrame): The GeoDataFrame from which columns will be removed
    gdf2 (GeoDataFrame): The GeoDataFrame that provides the column template
    
    Returns:
    GeoDataFrame: A new GeoDataFrame with only the columns present in gdf2
    """
    columns_to_keep = gdf_with_correct_columns.columns
    gdf1_filtered = gdf_to_be_adapted[columns_to_keep]
    return gdf1_filtered

def compute_difference_geodataframe(gdf_to_substract_from, gdf_to_substract, column_name):
    """
    Compute the difference of a specified column between two GeoDataFrames.
    
    Parameters:
    gdf1 (GeoDataFrame): The first GeoDataFrame
    gdf2 (GeoDataFrame): The second GeoDataFrame
    column_name (str): The column name for which to compute the difference
    
    Returns:
    GeoDataFrame: A new GeoDataFrame with the differences for the specified column
    """
    # Ensure the two GeoDataFrames have the same shape
    if gdf_to_substract_from.shape != gdf_to_substract.shape:
        raise ValueError("GeoDataFrames must have the same shape")

    # Ensure the two GeoDataFrames have the same indices
    if not gdf_to_substract_from.index.equals(gdf_to_substract.index):
        raise ValueError("GeoDataFrames must have the same indices")
    
    # Ensure the two GeoDataFrames have the same geometries
    if not gdf_to_substract_from.geometry.equals(gdf_to_substract.geometry):
        raise ValueError("GeoDataFrames must have the same geometries")
    
    # Create a copy of the first GeoDataFrame to use as the base for the difference GeoDataFrame
    difference_gdf = gdf_to_substract_from.copy()

    # Convert columns to numeric, coercing errors to NaN
    values_from = pd.to_numeric(gdf_to_substract_from[column_name], errors='coerce')
    values_to_substract = pd.to_numeric(gdf_to_substract[column_name], errors='coerce')

    # Compute the difference for the specified column
    difference_gdf[column_name] = values_from - values_to_substract
    
    # Compute percentage difference, avoiding division by zero
    difference_gdf[column_name + "_percentage_difference"] = (
        (difference_gdf[column_name] / values_to_substract * 100)
        .replace([np.inf, -np.inf], np.nan)  # Replace infinities with NaN
    )
    
    # Clip percentage differences to ±100%
    difference_gdf[column_name + "_clipped_percentage_difference"] = np.clip(
        difference_gdf[column_name + "_percentage_difference"], 
        -100, 
        100
    )
 
    return difference_gdf

random_seed_2_df_scenario_output_links = create_dic_seed_to_output_links(subdir=scenario_subdir_path)
random_seed_2_df_scenario_trips = create_dic_seed_to_eqasim_trips_given_output_trips(subdir=scenario_subdir_path)


scenario_output_links_gdfs = list(random_seed_2_df_scenario_output_links.values())

gdf_scenario_mean = compute_average_or_median_geodataframe(geodataframes=scenario_output_links_gdfs, column_name="vol_car", is_mean=True)
gdf_scenario_mean = gdf_scenario_mean.rename(columns={"osm:way:highway": "highway"})
gdf_basecase_mean = gpd.read_file(base_dir / "data" / "basecases_mean" / city_name / f"{city_name}_basecase_average_output_links.geojson")
gdf_comparison_mean_extended = extend_geodataframe(gdf_base = gdf_basecase_mean, gdf_to_extend=gdf_scenario_mean, column_to_extend='highway', new_column_name='highway')
gdf_basecase_without_unnecessary_columns = remove_columns(gdf_with_correct_columns=gdf_comparison_mean_extended, gdf_to_be_adapted=gdf_basecase_mean)
gdf_basecase_difference = compute_difference_geodataframe(gdf_to_substract_from=gdf_comparison_mean_extended, gdf_to_substract=gdf_basecase_without_unnecessary_columns, column_name= 'vol_car')
create_scenario_output_links_mean_file(city_name=city_name,gdf_scenario_mean=gdf_comparison_mean_extended)
create_difference_output_links_mean_file(city_name=city_name,gdf_difference_mean=gdf_basecase_difference)


plot_scenario_mean_file(city_name=city_name)
gdf_scenario_mean = calculate_edge_metrics(simulation_gdfs=scenario_output_links_gdfs, mean_gdf=gdf_scenario_mean)
print_edge_metrics(gdf_scenario_mean)
plot_edge_metrics(gdf_scenario_mean)

scenario_trips_dfs = list(random_seed_2_df_scenario_trips.values())
df_average_mode_stats = calculate_avg_mode_stats(scenario_trips_dfs)
create_scenario_trips_mean_file(city_name=city_name,df_scenario_trips=df_average_mode_stats)





            # Calculate total volume statistics
total_volume_before = scenario_edges['vol_car'].sum()
total_volume_after = total_volume_before * capacity_tuning_factor
volume_decrease = total_volume_before - total_volume_after
volume_decrease_percentage = (volume_decrease / total_volume_before) * 100 if total_volume_before > 0 else 0
            
print(f"Total car volume before capacity reduction: {total_volume_before:.2f}")
print(f"Total car volume after capacity reduction: {total_volume_after:.2f}")
print(f"Total car volume decrease: {volume_decrease:.2f} ({volume_decrease_percentage:.2f}%)")
            