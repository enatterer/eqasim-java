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

def unique_mode_extractor(df_output_links):
    unique_modes = df_output_links['modes'].unique()
    return unique_modes
    
if __name__ == "__main__":
    mode_dict = {}
    city_name = ["rosenheim","muenchen","schweinfurt","bamberg","aschaffenburg","erlangen","kempten","fuerth","landshut","bayreuth","ingolstadt","regensburg","wuerzburg","augsburg","nuernberg","neuulm"]
    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    for city in city_name:
        print('Processing city: ' + city)
        basecase_subdir_path = base_dir / "data" / "simulation_output" / "basecases_new" / city
        basecase_subdir_folder_seed_1 = basecase_subdir_path / f"{city}_seed_1"
        df_output_links = read_output_links(folder=basecase_subdir_folder_seed_1)
        unique_modes = unique_mode_extractor(df_output_links)
        #print(unique_modes)
        mode_dict[city] = unique_modes
    all_modes = np.concatenate(list(mode_dict.values()))
    final_unique_modes = np.unique(all_modes)
    #print(final_unique_modes)
    
    nonrepeating_final_unique_modes = set()
    for items in final_unique_modes:
        if isinstance(items, str):
            subitems=items.split(",")
            nonrepeating_final_unique_modes.update(subitems)
    print(nonrepeating_final_unique_modes)
    
