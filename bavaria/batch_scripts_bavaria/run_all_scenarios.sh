#!/bin/bash

#SBATCH -J simulation_augsburg_job_array
#SBATCH --output=simulation_augsburg_output_job_id%j.log
#SBATCH --error=simulation_augsburg_error_job_id%j.log

#SBATCH --nodes=13
#SBATCH --ntasks-per-node=8
#SBATCH --cpus-per-task=6
#SBATCH --mem=80GB
#SBATCH --time=24:00:00
#SBATCH --array=0

#SBATCH --account=pn39mu
#SBATCH --partition=micro
#SBATCH --mail-type=BEGIN,FAIL,END
#SBATCH --mail-user=ankit.basu@tum.de
#SBATCH --get-user-env
#SBATCH --export=ALL

# Setup environment
export HOME=/dss/dsshome1/05/go69tef3
export SCRATCH=/hppfs/scratch/05/go69tef3/bavaria_simulation_output
export FONTCONFIG_PATH=$HOME/test_java_font_4u/fonts
export FONTCONFIG_FILE=$HOME/test_java_font_4u/fonts/fonts.conf
export FC_FONT_PATH=$HOME/test_java_font_4u/fonts
export PATH=$HOME/java-21/bin:$PATH

BLOCK_SIZE=104
START_INDEX=$((SLURM_ARRAY_TASK_ID * BLOCK_SIZE))
END_INDEX=$((START_INDEX + BLOCK_SIZE - 1))

export START_INDEX
export END_INDEX
export BLOCK_SIZE

# Launch one srun per task in the allocation (each will get a unique SLURM_PROCID)
srun --mem=10GB bavaria/batch_scripts_bavaria/run_scenario_augsburg.sh 