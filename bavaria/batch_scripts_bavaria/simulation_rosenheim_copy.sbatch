#!/bin/bash

#SBATCH -J simulation_rosenheim_job
#SBATCH --output=simulation_rosenheim_output_job_id%j.log
#SBATCH --error=simulation_rosenheim_error_job_id%j.log

#SBATCH --nodes=2
#SBATCH --ntasks-per-node=15
#SBATCH --cpus-per-task=3
#SBATCH --mem=80GB
#SBATCH --time=00:30:00

#SBATCH --account=pn39mu
#SBATCH --partition=test
#SBATCH --mail-type=BEGIN,ERROR,END
#SBATCH --mail-user=ankit.basu@tum.de
#SBATCH --get-user-env
#SBATCH --export=ALL

# Setup environment
export HOME=/dss/dsshome1/05/go69tef3
export FONTCONFIG_PATH=$HOME/test_java_font_4u/fonts
export FONTCONFIG_FILE=$HOME/test_java_font_4u/fonts/fonts.conf
export FC_FONT_PATH=$HOME/test_java_font_4u/fonts
export PATH=$HOME/java-21/bin:$PATH

SCENARIO_FILE=bavaria/data/scenario_text_files/rosenheim/rosenheim_seed1_hexagon_all.txt
memory=1
threads=1

mapfile -t scenarios < "$SCENARIO_FILE"

max_parallel_jobs=$(( SLURM_NNODES * SLURM_NTASKS_PER_NODE ))  # 30

for i in "${!scenarios[@]}"; do
    read city road_type scenario_id seed hexagon_size mean_factor std_factor <<< "${scenarios[$i]}"
    logfile="output_${city}_${road_type}_s${scenario_id}_job_id${SLURM_JOB_ID}_subgraph$((i+1)).log"
    echo "[$(date)] Launching scenario $scenario_id on $(hostname) [task $i]" >> "$logfile"

    srun --ntasks=1 --ntasks-per-node=1 --cpus-per-task=3 --mem=5G --cpu-bind=cores java -Xmx1536m -cp bavaria/target/bavaria-1.5.0.jar \
        org.eqasim.bavaria.RunMultipleSimulationScenarios \
        --city "$city" --road_type "$road_type" --scenario "$scenario_id" --threads "$threads" --memory "$memory" \
        --seed "$seed" --hexagon_size "$hexagon_size" --mean_factor "$mean_factor" --std_factor "$std_factor" \
        > "$logfile" 2>&1 &

    # Wait for a slot if max_parallel_jobs are running
    while (( $(jobs -r | wc -l) >= max_parallel_jobs )); do
        wait -n
    done
done

wait  # Final wait for any leftovers