#!/bin/bash

#SBATCH -J simulation_basecases_job

# Output and error files
#SBATCH --output=simulation_basecases_output_%j.log
#SBATCH --error=simulation_basecases_error_%j.log

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=12
#SBATCH --cpus-per-task=4
#SBATCH --mem=80GB
#SBATCH --time=48:00:00

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

# Initialize process counter
declare -i process_count=0
max_processes=12  # Number of parallel processes to run (12 per node × 1 nodes)

# Function to wait for processes if we've reached the maximum
wait_for_processes() {
    while (( process_count >= max_processes )); do
        wait -n
        process_count=$((process_count - 1))
        echo "Process completed. Currently running: $process_count processes"
    done
}

# Run simulations for each city and seed
for seed in {0..48}; do
    for city in aschaffenburg augsburg bamberg bayreuth; do
        wait_for_processes
        echo "Starting simulation for $city with seed $seed (Process count: $process_count)"
        java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds \
            --city $city \
            --seeds $seed \
            --threads 4 \
            --memory 6 > ${city}_${seed}.log 2>&1 &
        process_count=$((process_count + 1))
        echo "Launched process for $city with seed $seed (Process count: $process_count)"
    done
done

# Wait for all remaining processes to complete
echo "Waiting for all remaining processes to complete..."
wait

echo "All simulations completed"
