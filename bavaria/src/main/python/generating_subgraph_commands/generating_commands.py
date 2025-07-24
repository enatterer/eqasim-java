import pandas as pd
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
# specify the following parameters
mean_factor = 4
std_factor = 8
seed_number = 3
hexagon_sizes = [500, 1000, 2000]


def read_table(base_dir):
    filename = base_dir / "data" / "optimization_table" / 'city_contributions.csv'
    dataframe = pd.read_csv(filename,delimiter=';')
    city_name = dataframe['City']
    contribution_500 = dataframe['contribution_500']
    contribution_1000 = dataframe['contribution_1000']
    contribution_2000 = dataframe['contribution_2000']
    return city_name, contribution_500, contribution_1000, contribution_2000


def generate_commands(base_dir):
    city_name, contribution_500, contribution_1000, contribution_2000 = read_table(base_dir)
    for i in range(len(city_name)):
        hex_sizes_str = ' '.join(str(x) for x in hexagon_sizes)
        subgraph_counts_str = f"{contribution_500[i]} {contribution_1000[i]} {contribution_2000[i]}"
        log_file = f"{city_name[i]}_subgraph_creation_new.log"
        print(f"nohup python3 bavaria/src/main/python/creating_subgraphs/subgraph_creation.py {city_name[i]} --seed_number {seed_number} --hexagon_sizes {hex_sizes_str} --mean_factors {mean_factor} --std_factors {std_factor} --subgraph_counts {subgraph_counts_str} > {log_file} 2>&1 &")

if __name__ == "__main__":
    generate_commands(base_dir)