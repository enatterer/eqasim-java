from pathlib import Path

cities = ["rosenheim","muenchen","schweinfurt","bamberg"]
small_cities = ["rosenheim","schweinfurt","bamberg"]
road_type = "primary"
seed = 2
hexagon_sizes = [500,1000,2000]
mean_factor = 4
std_factor = 8

base_dir = Path(__file__).parent.parent.parent.parent.parent.parent
subgraph_folder_path = base_dir / "bavaria" / "data" / "subgraph" / "network_files"


def save_to_different_text_file(filenames, output_dir):
    for key, value in filenames.items():
        output_path = Path(output_dir) / f"{city}_seed{seed}_hexagon_size{key}.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "a") as f:
            for text in value:
                f.write(f"{text}\n")
        print(f"Saved {len(value)} scenarios to {city}_seed{seed}_hexagon_size{key}.txt")

def save_to_one_text_file(filenames, output_dir):
    output_path = Path(output_dir) / f"{city}_seed{seed}_hexagon_all.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "a") as f:
        for scenario_list in filenames.values():
            for text in scenario_list:
                f.write(f"{text}\n")
                count += 1
    print(f"Saved {count} scenarios to {city}_seed{seed}_hexagon_all.txt")

if __name__ == "__main__":
    filenames = {}
    for city in ["schweinfurt"]:
        output_dir = base_dir / "bavaria" / "data" / "scenario_text_files"/f"{city}"
        for hexagon_size in hexagon_sizes:
            scenario_files = list(subgraph_folder_path.glob(f"{city}/{city}_seed_{seed}_hex{hexagon_size}_mean{mean_factor}_std{std_factor}/networks/network_seed{seed}_{city}_{road_type}_n*_s*.xml.gz"))
            scenario_text = []
            for scenario_file in scenario_files:
                s_part = scenario_file.name.split("_")[-1]
                scenario = s_part.split(".")[0][1:]
                text = f"{city} {road_type} {scenario} {seed} {hexagon_size} {mean_factor} {std_factor}"
                scenario_text.append(text)
            filenames[hexagon_size] = scenario_text
        if city in small_cities:
            save_to_one_text_file(filenames, output_dir)
        else:
            save_to_different_text_file(filenames, output_dir)
