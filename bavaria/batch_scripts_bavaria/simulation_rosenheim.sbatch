#!/bin/bash

#SBATCH -J simulation_rosenheim_job

# Output and error files
#SBATCH --output=simulation_rosenheim_output_job_id%j.log
#SBATCH --error=simulation_rosenheim_error_job_id%j.log

#SBATCH --nodes=2
#SBATCH --ntasks-per-node=15
#SBATCH --cpus-per-task=3
#SBATCH --mem=80GB
#SBATCH --time=00:30:00

# Account and partition
#SBATCH --account=pn39mu
#SBATCH --partition=test

# Notification and type
#SBATCH --mail-type=BEGIN,ERROR,END
#SBATCH --mail-user=ankit.basu@tum.de
#SBATCH --get-user-env

# Set up of execution environment
#SBATCH --export=none

#export HOME=/dss/dsshome1/05/go69tef3
export FONTCONFIG_PATH=$HOME/test_java_font_4u/fonts
export FONTCONFIG_FILE=$HOME/test_java_font_4u/fonts/fonts.conf
export FC_FONT_PATH=$HOME/test_java_font_4u/fonts

# Get scenario IDs (example: from filenames)
city = "rosenheim"
road_type = "primary"
threads = 3 #should be less than or equal to the number of cpus per task
memory = 5.5 #different from the node memory. (memory for each simulation times tasks per node should be less than node memory)
seed = 1
hexagon_size = "500"
mean_factor = 4
std_factor = 8
job_id = 1

declare -A SCENARIOS
for city in $cities; do    
    for road_type in $road_types; do
        for hexagon_size in $hexagon_sizes; do
            SCENARIO_FILES=(bavaria/data/subgraph/network_files/$city/$city_seed_$seed_hex$hexagon_size_mean$mean_factor_std$std_factor/networks/network_seed$seed_$city_$road_type_n*_s*.xml.gz)
            for FILE in "${SCENARIO_FILES[@]}"; do
                SCENARIO=$(echo "$FILE" | sed -n 's/.*_s\([0-9]*\)\.xml\.gz/\1/p')
                SCENARIOS["$city,$hexagon_size"]+="$SCENARIO"
            done
        done
    done
done

echo "Batch started at: $(date '+%Y-%m-%d %H:%M:%S')"
batch_start_time=$(date '+%s')

# Launch all simulations in the background
for city in $cities; do
    for hexagon_size in $hexagon_sizes; do
        FILES=(${SCENARIOS["$city,$hexagon_size"]})
        for FILE in ${FILES[@]}; do #replace with ${FILES[@]} to run all scenarios, except it runs only for the first scenario
            java -Xmx$memory"g" -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunMultipleSimulationScenarios \
                --city $city --road_type $road_type --scenario $scenario --threads $threads --memory $memory \
                --seed $seed --hexagon_size $hexagon_size --mean_factor $mean_factor --std_factor $std_factor \
                > output_${city}_${road_type}_s${scenario}_job_id${job_id}.log 2>&1 &
        done
    done
done

wait

batch_end_time=$(date '+%s')
batch_duration=$((batch_end_time - batch_start_time))
echo "Batch finished at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Total batch duration: ${batch_duration}s"

echo "All simulations finished."

