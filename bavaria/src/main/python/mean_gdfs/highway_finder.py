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

def read_output_links(folder):
    file_path = os.path.join(folder, 'output_links.csv.gz')
    if os.path.exists(file_path):
        try:
            # Read the CSV file with the correct delimiter
            df = pd.read_csv(file_path, delimiter=';',low_memory=False)
            return df
        except Exception:
            print("empty data error" + file_path)
            return None
    else:
        return None
    
if __name__ == "__main__":
    highway_dict = {}
    city_name = ["rosenheim","muenchen","schweinfurt","bamberg","aschaffenburg","erlangen","kempten","fuerth","landshut","bayreuth","ingolstadt","regensburg","wuerzburg","augsburg","nuernberg","neuulm"]
    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    for city in city_name:
        print('Processing city: ' + city)
        basecase_subdir_path = base_dir / "data" / "simulation_output" / "basecases_new" / city
        basecase_subdir_folder_seed_1 = basecase_subdir_path / f"{city}_seed_1"
        df_output_links = read_output_links(folder=basecase_subdir_folder_seed_1)
        df_output_links = df_output_links.rename(columns={"osm:way:highway": "highway"})
        unique_highways = df_output_links['highway'].unique()
        highway_dict[city] = unique_highways
    all_highways = set(np.concatenate(list(highway_dict.values())))
    print(all_highways)