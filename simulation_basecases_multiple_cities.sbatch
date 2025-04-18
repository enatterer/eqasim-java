#!/bin/bash

#SBATCH -J simulation_basecases_job

# Output and error files
#SBATCH --output=simulation_basecases_output_%j.log
#SBATCH --error=simulation_basecases_error_%j.log

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=24
#SBATCH --cpus-per-task=2
#SBATCH --mem=80GB
#SBATCH --time=02:30:00

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

# First city: kempten
for seed in {13..48}; do
    java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds \
        --city kempten \
        --seeds $seed \
        --threads 2 \
        --memory 2 > kempten_${seed}.log 2>&1 &

    java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds \
        --city neuulm \
        --seeds $seed \
        --threads 2 \
        --memory 2 > neuulm_${seed}.log 2>&1 &
done

wait

echo "All simulations completed"
