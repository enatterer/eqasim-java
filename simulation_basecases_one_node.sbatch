#!/bin/bash

#SBATCH -J simulation_basecases_job

# Output and error files
#SBATCH --output=simulation_basecases_output_%j.log
#SBATCH --error=simulation_basecases_error_%j.log

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=12
#SBATCH --cpus-per-task=4
#SBATCH --mem=80GB
#SBATCH --time=03:30:00

# Account and partition
#SBATCH --account=pn39mu
#SBATCH --partition=micro

# Notification and type
#SBATCH --mail-type=BEGIN,END
#SBATCH --mail-user=elena.natterer@tum.de
#SBATCH --get-user-env

# Set up of execution environment
#SBATCH --export=none

export FONTCONFIG_PATH=$HOME/test_java_font_4u/fonts
export FONTCONFIG_FILE=$HOME/test_java_font_4u/fonts/fonts.conf
export FC_FONT_PATH=$HOME/test_java_font_4u/fonts

# Initialize process counter and tracking array
declare -i process_count=0
max_processes=12  # Number of parallel processes to run (12 per node × 1 nodes)
declare -A process_map  # Array to map PIDs to city_seed combinations

# Function to wait for processes if we've reached the maximum
wait_for_processes() {
    while (( process_count >= max_processes )); do
        wait -n
        process_count=$((process_count - 1))
        exit_status=$?
        # Get the PID of the completed process
        completed_pid=$!
        # Get the city_seed from our tracking array
        city_seed=${process_map[$completed_pid]}
        echo "Process completed for $city_seed with exit status $exit_status. Currently running: $process_count processes"
        # Remove the completed process from our tracking array
        unset process_map[$completed_pid]
    done
}

# Run simulations for each city and seed
for seed in {1..48}; do
    for city in muenchen fuerth nuernberg wuerzburg; do
        wait_for_processes
        echo "Starting simulation for $city with seed $seed (Process count: $process_count)"
        java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds \
            --city $city \
            --seeds $seed \
            --threads 4 \
            --memory 6 \
            --config-path "$CONFIG_PATH" \
            --network-path "$NETWORK_PATH" > ${city}_${seed}.log 2> ${city}_${seed}_error.log & 
        
        pid=$!
        process_map[$pid]="${city}_${seed}"
        process_count=$((process_count + 1))
        echo "Launched process for $city with seed $seed (Process count: $process_count)"
    done
done

# Wait for all remaining processes to complete
echo "Waiting for all remaining processes to complete..."
wait

echo "All simulations completed"
