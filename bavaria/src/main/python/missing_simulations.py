from pathlib import Path
import random

seed = 2

base_dir = Path(__file__).parent.parent.parent.parent.parent
missing_simulations_dir = base_dir / "bavaria" / "data" / "scenario_text_files"
scenario_text_files_dir = base_dir / "bavaria" / "data" / "scenario_text_files"
scenario_text_files_dir_new = base_dir / "bavaria" / "data" / "scenario_text_files_new"

for city in ["muenchen"]:
    missing_simulations_text_file_path = missing_simulations_dir / city / "missing_simulations_hex_500.txt"
    scenario_text_file_path = scenario_text_files_dir / city / f"{city}_seed{seed}_hexagon_size500.txt"
    scenario_text_file_path_new = scenario_text_files_dir_new / city / f"{city}_seed{seed}_hexagon_size500.txt"

    # Read all scenario lines and build a lookup dictionary for fast access
    scenario_lookup = {}
    with open(scenario_text_file_path, "r") as scenario_file:
        for line in scenario_file:
            parsed_line = line.strip().split(" ")
            if len(parsed_line) > 2:
                scenario_lookup[parsed_line[2]] = line  # key: the third field

    # Read all missing simulation lines
    with open(missing_simulations_text_file_path, "r") as f:
        lines = f.readlines()

    # Ensure output directory exists
    scenario_text_file_path_new.parent.mkdir(parents=True, exist_ok=True)

    # Open the output file once in write mode to clear it at the start
    with open(scenario_text_file_path_new, "w") as out_file:
        for line in lines:
            parsed_line_1 = line.strip().split("/")
            parsed_line_2 = parsed_line_1[0].split("_")
            parsed_line_num = parsed_line_2[3].lstrip("s")
            # Write the matching scenario line if found
            if parsed_line_num in scenario_lookup:
                out_file.write(scenario_lookup[parsed_line_num])
                print(f"Added {parsed_line_num} to {scenario_text_file_path_new}")
            else:
                print(f"Warning: {parsed_line_num} not found in {scenario_text_file_path}")