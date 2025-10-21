# eqasim_bavaria
# MATSim Network Intervention Analysis for Bavarian Cities

Overview:
This file walks you through creating subgraphs from MATSim network outputs, preparing scenario network files with modified link capacities, and running those scenarios in parallel on HPC clusters. It outlines the end-to-end workflow from extracting and sampling network subsets, generating MATSim-compatible subgraph networks, producing batch submission text files, to executing and monitoring parallel simulation runs and aggregating results for analysis.

## Repository Structure

```
eqasim_bavaria/
├── bavaria/
│   ├── data/                           # Data storage and results
│   │   ├── city_boundaries/            # Administrative boundaries (GeoJSON)
│   │   ├── simulation_input/           # MATSim network files (Intermediate from Cut Simulations Java Class)
│   │   ├── simulation_output/          # Simulation results
│   │   ├── subgraph/                   # Generated network scenarios (subgraphs with modified capacity on links)
│   │   ├── basecases_mean/             # Averaged baseline data (averaged across all the runs)
│   │   ├── scenario_mean/              # Averaged scenario data (aggregated statistics of each scenario run)
│   │   ├── difference_mean/            # Difference analysis results (scenario mean - basecase mean)
│   │   ├── scenario_text_files/        # Batch processing parameters (for parallel processing in HPC)
│   │   └── optimization_table/         # City-specific scenario configuration parameters
│   │       └── city_contributions.csv  # Target subgraph counts per city and hexagon size
|   |
│   ├── batch_scripts_bavaria/          # HPC batch processing scripts
│   │   ├── run_all_scenarios.sh        # Common execution script for all cities
│   │   ├── {city_name}_job.sh          # City-specific SLURM job scripts
│   │  
│   └── src/main/python/
│       ├── creating_subgraphs/         # Core analysis modules for creating subgraphs of each city
│       ├── generating_subgraph_commands/ # Command generation
│       ├── mean_gdfs/                  # Analysis and Plotting
│       └── scenario_text_generator/    # Batch file generation for parallel simulation runs in HPC
└── README.md                           # This file
```

## Supported Cities

**Bavarian Cities**: Munich, Augsburg, Nuremberg, Neu-Ulm , Rosenheim, Schweinfurt, Aschaffenburg, Erlangen, Kempten, Fürth, Landshut, Bayreuth, Ingolstadt, Bamberg, Regensburg, Würzburg


## Complete Workflow (From subgraph generation to simulation to analysis)

### Phase 1: Network Preparation & Scenario Generation
```
bavaria/src/main/python/creating_subgraphs/subgraph_creation.py [for controlling different parameters]
bavaria/src/main/python/generating_subgraph_commands/generating_commands.py [for generating commands to create scenarios for each city]
```

### Phase 2: Simulation Execution
```
bavaria/src/main/python/scenario_text_generator/scenario_text_generator.py [to create text file before submiting batch scripts]
bavaria/batch_scripts_bavaria/run_all_scenarios.sh [to simulate multiple scenarios in parallel in HPC using batch scripts]
```

### Phase 3: Statistical Analysis
```
bavaria/src/main/python/mean_gdfs/create_basecase_means.py (for basecase simulation outputs)
bavaria/src/main/python/mean_gdfs/create_scenario_means.py (for scenario simulation outputs)
```

### Phase 4: Visualization
```
bavaria/src/main/python/mean_gdfs/comparison_plot.py (for final visualization and comparison)
```


## Core Modules

### 1. Subgraph Creation Pipeline (`creating_subgraphs/`)

#### `subgraph_creation.py`
**Main orchestration module** for generating network intervention scenarios.

**Process Flow**:
1. Creates hexagonal grid overlay for target city
2. Calculates edge centrality measures (betweenness/closeness)
3. Generates subgraphs for primary roads meeting centrality criteria (primary roads for our use-case, adjust accordingly)
4. Creates MATSim network files with modified link capacities
5. Saves scenario data (hexagon IDs, edge geometries, network files)

### 2. Command Generation (`generating_subgraph_commands/`)

#### `generating_commands.py`
Generates nohup commands for batch processing multiple cities.

### 3. Analysis and Plotting (`mean_gdfs/`)

#### `create_basecase_means.py`
Processes multiple simulation runs to create averaged baseline datasets.
**Output Files**:
- `{city}_basecase_average_output_links.geojson`: Averaged network with traffic volumes
- `{city}_basecase_average_trips.csv`: Mode-specific trip statistics
- `{city}_traffic_volume_map.png`: Traffic volume visualization

#### `create_scenario_means.py`
Analyzes each scenario simulation results of a city and compares against its respective baseline.

**Output Files**:
- `{city}_{road_type}_network_s{scenario}_scenario_average_output_links.geojson`
- `{city}_{road_type}_network_s{scenario}_difference_average_output_links.geojson`
- `{city}_{road_type}_network_s{scenario}_scenario_average_trips.csv`

#### `comparison_plot.py`
Creates sophisticated comparative visualizations showing intervention impacts in a city (in our use case: difference in car volume in links [scenario - basecase]).

**Visualization Layers**:
1. **Base network**: All roads in target zone (thin lines)
2. **Target road types**: Roads of intervention type in hexagons (medium lines)
3. **Capacity-reduced roads**: Roads with actual capacity reduction (thick lines with borders)
4. **Selected hexagons**: Intervention area boundaries (green outlines)
5. **Zone boundaries**: Study area limits (black outlines)

### 4. Batch Processing (`scenario_text_generator/`)

#### `scenario_text_generator.py`
Generates text files for MATSim batch processing management in HPC.

### Optimization Configuration
```
data/optimization_table/city_contributions.csv
```
**Required CSV file** containing city-specific target subgraph counts for scenario generation.

**CSV Format**:
```csv
City;contribution_500;contribution_1000;contribution_2000
augsburg;2946;3000;31
erlangen;1234;1500;25
muenchen;5000;5200;45
...
```

**Column Descriptions**:
- `City`: City name (must match directory names in other data folders)
- `contribution_500`: Target number of subgraphs for 500m hexagon grid
- `contribution_1000`: Target number of subgraphs for 1000m hexagon grid  
- `contribution_2000`: Target number of subgraphs for 2000m hexagon grid

**Usage**: Read by `generating_commands.py` to create city-specific command parameters for the `--subgraph_counts` argument in subgraph creation.

**Note**: The optimization table determines how many scenarios are generated for each city-hexagon size combination, directly affecting computational requirements and analysis scope. Refer to the optimization techniques used to arrive at out subgraph count
per city at https://www.overleaf.com/project/67f386f04fb670464d9bdd66 (if this overleaf file doesnot open, link the arxiv link--to do later)

## HPC Parallel Processing
This section explains how to prepare, dispatch and monitor large numbers of scenario simulations on an HPC system. It covers creating per-city scenario text files, preparing SLURM job scripts, submitting jobs, and monitoring progress and logs. Follow these steps to run many scenario permutations in parallel while tuning resource requests and parallelization granularity for your cluster.
### Batch Scripts Setup
The `batch_scripts_bavaria/` directory contains optimized SLURM scripts for HPC clusters:

- **`run_all_scenarios.sh`**: Common execution logic shared across all cities
- **`{city}_job.sh`**: City-specific resource allocation (nodes, memory, time)

### HPC Workflow

1. **Generate scenario text files**: `python3 scenario_text_generator.py`
2. **Submit city jobs**: `sbatch {city}_job.sh`
3. **Monitor progress**: `squeue -u $USER | grep bavaria`

Each city job reads from `scenario_text_files/{city}/` and processes scenarios in parallel using the shared `run_all_scenarios.sh` script with city-specific resource allocation.
Adjust logging and resource parameters in {city}_job.sh and run_all_scenarios.sh to match cluster policies and throughput requirements.



