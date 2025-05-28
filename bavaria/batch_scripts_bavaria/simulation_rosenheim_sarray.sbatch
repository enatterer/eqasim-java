#!/bin/bash

#SBATCH -J simulation_rosenheim_job
#SBATCH --array=1-15
#SBATCH --output=simulation_rosenheim_output_job_id%j.log
#SBATCH --error=simulation_rosenheim_error_job_id%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=3
#SBATCH --mem=80GB
#SBATCH --time=00:30:00
#SBATCH --account=pn39mu
#SBATCH --partition=test
#SBATCH --mail-type=BEGIN,ERROR,END
#SBATCH --mail-user=ankit.basu@tum.de
#SBATCH --get-user-env
#SBATCH --export=none

export FONTCONFIG_PATH=$HOME/test_java_font_4u/fonts
export FONTCONFIG_FILE=$HOME/test_java_font_4u/fonts/fonts.conf
export FC_FONT_PATH=$HOME/test_java_font_4u/fonts

# Get the scenario parameters for this array task
SCENARIO_FILE=bavaria/data/scenario_text_files/rosenheim/rosenheim_seed1_hexagon_all.txt
SCENARIO_LINE=$SLURM_ARRAY_TASK_ID
IFS=, read city road_type scenario seed hexagon_size mean_factor std_factor < <(sed -n "${SCENARIO_LINE}p" $SCENARIO_FILE)

memory=5.5 # or set dynamically if needed
threads=3

echo "Batch started at: $(date '+%Y-%m-%d %H:%M:%S')"
batch_start_time=$(date '+%s')

java -Xmx${memory}g -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunMultipleSimulationScenarios \
    --city $city --road_type $road_type --scenario $scenario --threads $threads --memory $memory \
    --seed $seed --hexagon_size $hexagon_size --mean_factor $mean_factor --std_factor $std_factor \
    > output_${city}_${road_type}_s${scenario}_job_id${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}.log 2>&1

batch_end_time=$(date '+%s')
batch_duration=$((batch_end_time - batch_start_time))
echo "Batch finished at: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Total batch duration: ${batch_duration}s"