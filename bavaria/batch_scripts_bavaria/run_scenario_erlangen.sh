#!/bin/bash

threads=2 #should match cpus-per-task
memory=2 #should be less than or equal to --mem in srun in run_all_scenarios.sh

SCENARIO_FILE=bavaria/data/scenario_text_files/erlangen/erlangen_seed3_hexagon_all.txt
mapfile -t scenarios < "$SCENARIO_FILE"
i=$((START_INDEX + SLURM_PROCID))

if [ $i -ge ${#scenarios[@]} ]; then
    exit 0
fi

read city road_type scenario_id seed hexagon_size mean_factor std_factor <<< "${scenarios[$i]}"
logfile="output_${city}_${road_type}_s${scenario_id}_job_id${SLURM_JOB_ID}_subgraph$((i+1)).log"
echo "[$(date)] Launching scenario $scenario_id on $(hostname) [task $i]" >> "$logfile"
java -Xmx"$memory"g -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunMultipleSimulationScenarios \
    --city "$city" --road_type "$road_type" --scenario "$scenario_id" --threads "$threads" --memory "$memory" \
    --seed "$seed" --hexagon_size "$hexagon_size" --mean_factor "$mean_factor" --std_factor "$std_factor" \
    --output_dir "$SCRATCH" \
    > "$logfile" 2>&1 