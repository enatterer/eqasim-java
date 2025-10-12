"""
Scenario Text File Generator for MATSim Simulation Batch Processing

This module generates text files containing scenario parameters for batch execution
of MATSim network intervention simulations. It processes generated subgraph networks
and creates organized parameter lists for distributed computing and simulation management.

Key Operations:
    1. Scan subgraph network directories for generated scenario files
    2. Extract scenario parameters from file naming patterns
    3. Generate text files with scenario specifications for batch processing
    4. Organize scenarios by city, hexagon size, and sampling strategies
    5. Support multiple output formats (grouped, sampled, comprehensive)

Output Formats:
    - Grouped files: Split scenarios into manageable batch sizes
    - Random samples: Multiple random subsets for statistical analysis
    - Comprehensive files: All scenarios for complete analysis
    - Size-specific files: Scenarios organized by hexagon grid size

File Naming Convention:
    Input files: network_seed{seed}_{city}_{road_type}_n{network_id}_s{scenario}.xml.gz
    Output text: {city}_seed{seed}_hexagon_{format}.txt
    Content format: "{city} {road_type} {scenario} {seed} {hexagon_size} {mean_factor} {std_factor}"

Usage:
    python3 scenario_text_generator.py
    
    # Processes cities defined in main block
    # Reads from: bavaria/data/subgraph/network_files/
    # Outputs to: bavaria/data/scenario_text_files/{city}/

Configuration:
    Modify global variables for different processing:
    - cities: List of cities to process
    - hexagon_sizes: Grid sizes to include
    - seed, mean_factor, std_factor: Scenario parameters
    - group_size: Batch size for grouped output
    - sample_size, n_samples: Random sampling parameters

Requirements:
    - Generated subgraph network files from subgraph_creation.py
    - Consistent file naming convention across all scenarios
    - Sufficient disk space for text file generation
"""

from pathlib import Path
import random

# Configuration parameters
cities = ["rosenheim","muenchen","schweinfurt","bamberg","aschaffenburg","erlangen","kempten","fuerth","landshut","bayreuth","ingolstadt","regensburg","wuerzburg","augsburg","nuernberg","neuulm"]
small_cities = ["rosenheim","schweinfurt","aschaffenburg","kempten","fuerth",'landshut','erlangen','bayreuth','ingolstadt','bamberg','regensburg','wuerzburg']
road_type = "primary"
seed = 3
rand_seeds = 13
hexagon_sizes = [2000]
mean_factor = 4
std_factor = 8

base_dir = Path(__file__).parent.parent.parent.parent.parent.parent
subgraph_folder_path = base_dir / "bavaria" / "data" / "subgraph" / "network_files"


def save_to_different_text_file(filenames, output_dir):
    """
    Save scenario parameters to separate files organized by hexagon size.
    
    Creates individual text files for each hexagon grid size, enabling
    size-specific batch processing and parallel execution strategies.
    
    Args:
        filenames (dict): Hexagon size to scenario parameter list mapping
                         Keys: int (hexagon sizes)
                         Values: list of str (scenario parameter strings)
        output_dir (Path): Directory for output text files
        
    Saves:
        Text files named: {city}_seed{seed}_hexagon_size{size}.txt
        Each file contains scenario parameters, one per line
        
    Prints:
        Summary of scenarios saved for each hexagon size
        
    Note:
        Uses append mode - multiple runs will accumulate scenarios
        Global variables city and seed are used in file naming
    """
    for key, value in filenames.items():
        output_path = Path(output_dir) / f"{city}_seed{seed}_hexagon_size{key}.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "a") as f:
            for text in value:
                f.write(f"{text}\n")
        print(f"Saved {len(value)} scenarios to {city}_seed{seed}_hexagon_size{key}.txt")


def save_to_one_text_file(filenames, output_dir):
    """
    Save all scenario parameters to a single comprehensive text file.
    
    Combines scenarios from all hexagon sizes into one file for
    comprehensive batch processing or complete simulation runs.
    
    Args:
        filenames (dict): Hexagon size to scenario parameter list mapping
                         Keys: int (hexagon sizes)
                         Values: list of str (scenario parameter strings)
        output_dir (Path): Directory for output text file
        
    Saves:
        Single text file: {city}_seed{seed}_hexagon_all.txt
        Contains all scenarios across all hexagon sizes
        
    Prints:
        Total number of scenarios saved to comprehensive file
        
    Note:
        Uses append mode - multiple runs will accumulate scenarios
        Scenarios from different hexagon sizes are intermixed
    """
    output_path = Path(output_dir) / f"{city}_seed{seed}_hexagon_all.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(output_path, "a") as f:
        for scenario_list in filenames.values():
            for text in scenario_list:
                f.write(f"{text}\n")
                count += 1
    print(f"Saved {count} scenarios to {city}_seed{seed}_hexagon_all.txt")


def save_random_sample_scenarios(city, filenames, output_dir, sample_size=100, n_samples=5):
    """
    Generate multiple random samples of scenarios for statistical analysis.
    
    Creates several independent random subsets of scenarios, useful for
    statistical validation, uncertainty analysis, or resource-constrained studies.
    
    Args:
        city (str): City name for file naming
        filenames (dict): Hexagon size to scenario parameter list mapping
        output_dir (Path): Directory for output text files
        sample_size (int, optional): Number of scenarios per sample. Defaults to 100
        n_samples (int, optional): Number of independent samples to generate. Defaults to 5
        
    Saves:
        Text files named: {city}_seed{seed}_hexagon_sample{size}_{i}.txt
        Each file contains one random sample of scenarios
        
    Prints:
        Summary of scenarios saved for each random sample
        Warning if fewer scenarios available than requested sample size
        
    Note:
        Uses different random seeds for each sample to ensure independence
        Global variable rand_seeds provides base seed for reproducibility
        If insufficient scenarios, returns all available scenarios
    """
    all_scenarios = []
    for scenario_list in filenames.values():
        all_scenarios.extend(scenario_list)
        
    for i in range(1, n_samples + 1):
        if len(all_scenarios) < sample_size:
            print(f"Warning: Only {len(all_scenarios)} scenarios available, less than requested {sample_size}.")
            sample = all_scenarios
        else:
            random.seed(rand_seeds + i)  # Different seed for each sample
            sample = random.sample(all_scenarios, sample_size)
            
        output_path = Path(output_dir) / f"{city}_seed{seed}_hexagon_sample{sample_size}_{i}.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            for text in sample:
                f.write(f"{text}\n")
        print(f"Saved {len(sample)} random scenarios to {city}_seed{seed}_hexagon_sample{sample_size}_{i}.txt")


def split_scenarios_into_groups(city, filenames, output_dir, group_size=100):
    """
    Split all scenarios into sequential groups for batch processing management.
    
    Divides complete scenario list into manageable chunks, ideal for
    distributed computing, memory-constrained systems, or progress tracking.
    
    Args:
        city (str): City name for file naming
        filenames (dict): Hexagon size to scenario parameter list mapping
        output_dir (Path): Directory for output text files
        group_size (int, optional): Maximum scenarios per group file. Defaults to 100
        
    Saves:
        Text files named: {city}_seed{seed}_new_hexagon_sample{size}_{counter}.txt
        Each file contains sequential scenarios up to group_size limit
        
    Prints:
        Summary of scenarios saved for each group file
        
    Note:
        Uses sequential splitting (not random) - preserves original order
        Final group may contain fewer than group_size scenarios
        Useful for checkpoint-based processing and fault tolerance
    """
    all_scenarios = []
    for scenario_list in filenames.values():
        all_scenarios.extend(scenario_list)
        
    counter = 1
    for i in range(0, len(all_scenarios), group_size):
        sample = all_scenarios[i:i+group_size]
        output_path = Path(output_dir) / f"{city}_seed{seed}_new_hexagon_sample{group_size}_{counter}.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            for text in sample:
                f.write(f"{text}\n")
        print(f"Saved {len(sample)} random scenarios to {city}_seed{seed}_new_hexagon_sample{group_size}_{counter}.txt")
        counter += 1


if __name__ == "__main__":
    """
    Main execution block for scenario text file generation.
    
    Processes specified cities to generate scenario parameter files for
    MATSim batch processing. Scans subgraph network directories, extracts
    scenario information, and creates organized text files.
    
    Current Configuration:
        - Cities: Large cities (muenchen, augsburg, nuernberg, neuulm)
        - Output: Sequential groups of 3000 scenarios each
        - File pattern: network_seed{seed}_{city}_{road_type}_n*_s*.xml.gz
        
    Process:
        1. For each city, scan network file directories
        2. Extract scenario numbers from filenames
        3. Format scenario parameters as text strings
        4. Save organized text files using specified strategy
        
    Output Location:
        bavaria/data/scenario_text_files/{city}/
        
    File Content Format:
        Each line: "{city} {road_type} {scenario} {seed} {hexagon_size} {mean_factor} {std_factor}"
        
    Note:
        Uncomment alternative save functions for different output strategies:
        - save_random_sample_scenarios(): For statistical sampling
        - save_to_one_text_file(): For comprehensive files
        - save_to_different_text_file(): For size-specific files
    """
    for city in ['muenchen','augsburg','nuernberg','neuulm']:
        filenames = {}
        output_dir = base_dir / "bavaria" / "data" / "scenario_text_files" / f"{city}"
        
        for hexagon_size in hexagon_sizes:
            # Scan for scenario network files matching the pattern
            scenario_files = list(subgraph_folder_path.glob(
                f"{city}/{city}_seed_{seed}_hex{hexagon_size}_mean{mean_factor}_std{std_factor}/networks/network_seed{seed}_{city}_{road_type}_n*_s*.xml.gz"
            ))
            
            scenario_text = []
            for scenario_file in scenario_files:
                # Extract scenario number from filename
                s_part = scenario_file.name.split("_")[-1]
                scenario = s_part.split(".")[0][1:]  # Remove 's' prefix
                
                # Format scenario parameters
                text = f"{city} {road_type} {scenario} {seed} {hexagon_size} {mean_factor} {std_factor}"
                scenario_text.append(text)
            
            filenames[hexagon_size] = scenario_text
            print(f"Found {len(scenario_text)} scenarios for {city} with hexagon size {hexagon_size}")
        
        # Save scenarios using sequential grouping strategy
        split_scenarios_into_groups(city, filenames, output_dir, group_size=3000)
        
        # Alternative saving strategies (uncomment as needed):
        # save_random_sample_scenarios(city, filenames, output_dir, sample_size=200, n_samples=5)
        # save_to_one_text_file(filenames, output_dir)
        # save_to_different_text_file(filenames, output_dir)
        
        print(f"Completed scenario text generation for {city}")
