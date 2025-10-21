#!/bin/bash

# Node-specific script that runs simulations for a single node

# Get the node ID from the environment variable
node_id=$NODE_ID

# Define cities
cities=("aschaffenburg" "augsburg" "bamberg" "bayreuth" "erlangen" "landshut" "neuulm" "regensburg" "rosenheim")

# Print node information
echo "Running on node $node_id"
echo "Hostname: $(hostname)"
echo "CPUs per task: $SLURM_CPUS_PER_TASK"
echo "Memory per node: $SLURM_MEM_PER_NODE"

# Set up log file for this node
node_log="job_${SLURM_JOBID}_node_${node_id}.log"
echo "Starting simulations on node $node_id at $(date)" > "$node_log"

# Function to log messages
log_message() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message" | tee -a "$node_log"
}

# Initialize process counter
declare -i process_count=0
max_processes=4  # Maximum processes per node

# Function to wait for processes if we've reached the maximum
wait_for_processes() {
    while (( process_count >= max_processes )); do
        if wait -n; then
            process_count=$((process_count - 1))
            log_message "Process completed successfully. Currently running: $process_count processes"
        else
            process_count=$((process_count - 1))
            log_message "WARNING: A process failed. Currently running: $process_count processes"
            log_message "Process exit status: $?"
        fi
    done
}

# Calculate start and end seeds for this node
total_seeds=48
seeds_per_node=$((total_seeds / 4))  # 4 nodes total
start_seed=$((node_id * seeds_per_node + 1))
end_seed=$((start_seed + seeds_per_node - 1))

# Handle remaining seeds for the last node
if [ $node_id -eq 3 ]; then  # Last node (node 3) gets any remaining seeds
    end_seed=48
fi

log_message "Node $node_id will process seeds $start_seed to $end_seed"

# Run simulations for each city and seed
for ((seed=start_seed; seed<=end_seed; seed++)); do
    for city in "${cities[@]}"; do
        wait_for_processes
        
        # Create a separate log file for this simulation
        sim_log="${city}_${seed}.log"
        
        log_message "Starting simulation for $city with seed $seed (Process count: $process_count)"
        log_message "Output will be written to $sim_log"
        
        # Run the simulation with detailed error logging
        {
            echo "Starting Java process at $(date)"
            echo "Environment:"
            env | grep -E 'JAVA|PATH|FONT'
            echo "Command:"
            echo "java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds --city $city --seeds $seed --threads 12 --memory 20"
            
            java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds \
                --city $city \
                --seeds $seed \
                --threads 12 \
                --memory 20 2>&1
            
            echo "Java process ended at $(date) with exit code $?"
        } > "$sim_log" 2>&1 &
        
        sim_pid=$!
        log_message "Launched process for $city with seed $seed (PID: $sim_pid, Process count: $process_count)"
        process_count=$((process_count + 1))
        
        # Periodically check if the process is still running
        (
            while true; do
                if ! ps -p $sim_pid > /dev/null 2>&1; then
                    log_message "Process $sim_pid for $city seed $seed has terminated"
                    break
                fi
                log_message "Process $sim_pid for $city seed $seed is still running"
                sleep 300
            done
        ) &
    done
done

# Wait for all remaining processes to complete
log_message "Waiting for all remaining processes to complete..."
while (( process_count > 0 )); do
    if wait -n; then
        process_count=$((process_count - 1))
        log_message "Process completed successfully. Remaining: $process_count processes"
    else
        process_count=$((process_count - 1))
        log_message "WARNING: A process failed. Remaining: $process_count processes"
        log_message "Process exit status: $?"
    fi
done

log_message "All simulations completed"
exit 0 