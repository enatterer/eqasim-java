#!/bin/bash

#SBATCH -J simulation_rosenheim_job

# Output and error files
#SBATCH --output=simulation_rosenheim_output_%j.log
#SBATCH --error=simulation_rosenheim_error_%j.log

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=24
#SBATCH --cpus-per-task=2
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

export HOME=/dss/dsshome1/05/go69tef3
export FONTCONFIG_PATH=$HOME/test_java_font_4u/fonts
export FONTCONFIG_FILE=$HOME/test_java_font_4u/fonts/fonts.conf
export FC_FONT_PATH=$HOME/test_java_font_4u/fonts

# Loop over hexagon sizes and run the Java program for each
city = "rosenheim"
hex_size = 500
mean=4
std=8

for i in "city" ;do
    for j in "hex_size" ;do
        Files=(bavaria/data/subgraph/network_file/"$i"/"$i"_seed_1_hex"$j"_mean"$mean"_std"$std"/*)
        SCENARIOS=()
        for FILE in "${FILES[@]}"; do
            # Extract the scenario number after '_s' and before '.xml.gz'
            SCENARIO=$(echo "$FILE" | sed -n 's/.*_s\([0-9]*\)\.xml\.gz/\1/p')
            SCENARIOS+=("$SCENARIO")
        done
        SCENARIO_INDEX=$(($SLURM_ARRAY_TASK_ID - 1))
        SCENARIO=${SCENARIOS[$SCENARIO_INDEX]}
        ROAD_TYPE=primary

        java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunMultipleSimulationScenarios --city $i --seed 1 --road_type $ROAD_TYPE --scenario $SCENARIO --threads 2 --memory 80 --hex_size $j






java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunMultipleSimulationScenarios --city rosenheim --run_all --seed 1 --threads 2 --memory 80 --hex_size 500

done

