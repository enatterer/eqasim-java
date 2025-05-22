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


city_name = "rosenheim"

base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
basecase_subdir_path = base_dir / "data" / "simulation_output" / "basecases_new" / city_name
result_path_basecase_mean = base_dir / "data" / "basecases_mean"


def create_dic_seed_to_output_links(subdir):
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

def create_basecase_output_links_mean_file(city_name, gdf_basecase_mean):
    result_path_basecase_mean = base_dir / "data" / "basecases_mean" / city_name / f"{city_name}_basecase_average_output_links.geojson"
    # Create the directory structure if it doesn't exist
    result_path_basecase_mean.parent.mkdir(parents=True, exist_ok=True)
    gdf_basecase_mean.to_file(result_path_basecase_mean, driver='GeoJSON')

def plot_basecase_mean_file(city_name,): 
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

def create_basecase_trips_mean_file(city_name,df_basecase_trips):
    result_path_basecase_trips = base_dir / "data" / "basecases_mean" / city_name / f"{city_name}_basecase_average_trips.csv"
    # Create the directory structure if it doesn't exist
    result_path_basecase_trips.parent.mkdir(parents=True, exist_ok=True)
    df_basecase_trips.to_csv(result_path_basecase_trips, index=False)

def calculate_edge_metrics(simulation_gdfs, mean_gdf):
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

random_seed_to_df_basecase_output_links = create_dic_seed_to_output_links(subdir=basecase_subdir_path)
random_seed_to_df_basecase_trips = create_dic_seed_to_eqasim_trips_given_output_trips(subdir=basecase_subdir_path)


basecase_output_links_gdfs = list(random_seed_to_df_basecase_output_links.values())

gdf_basecase_mean = compute_average_or_median_geodataframe(geodataframes=basecase_output_links_gdfs, column_name="vol_car", is_mean=True)
gdf_basecase_mean = gdf_basecase_mean.rename(columns={"osm:way:highway": "highway"})
create_basecase_output_links_mean_file(city_name=city_name,gdf_basecase_mean=gdf_basecase_mean)
plot_basecase_mean_file(city_name=city_name)
gdf_basecase_mean = calculate_edge_metrics(simulation_gdfs=basecase_output_links_gdfs, mean_gdf=gdf_basecase_mean)
print_edge_metrics(gdf_basecase_mean)
plot_edge_metrics(gdf_basecase_mean)


basecase_trips_dfs = list(random_seed_to_df_basecase_trips.values())
df_average_mode_stats = calculate_avg_mode_stats(basecase_trips_dfs)
create_basecase_trips_mean_file(city_name=city_name,df_basecase_trips=df_average_mode_stats)










