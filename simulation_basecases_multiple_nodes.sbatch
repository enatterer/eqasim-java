#!/bin/bash

#SBATCH -J simulation_basecases_job

# Output and error files
#SBATCH --output=simulation_basecases_output_%j.log
#SBATCH --error=simulation_basecases_error_%j.log

#SBATCH --nodes=4
#SBATCH --ntasks-per-node=12
#SBATCH --cpus-per-task=4
#SBATCH --mem=80GB
#SBATCH --time=24:00:00

# Account and partition
#SBATCH --account=pn39mu
#SBATCH --partition=micro

# Notification and type
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=elena.natterer@tum.de
#SBATCH --get-user-env

# Set up of execution environment
#SBATCH --export=none

export FONTCONFIG_PATH=$HOME/test_java_font_4u/fonts
export FONTCONFIG_FILE=$HOME/test_java_font_4u/fonts/fonts.conf
export FC_FONT_PATH=$HOME/test_java_font_4u/fonts

# Get the node ID (0-based)
node_id=$SLURM_NODEID

# Define cities
cities=("fuerth" "landshut" "regensburg" "rosenheim")

# Print node information
echo "Running on node $node_id"
echo "Total nodes: $SLURM_NNODES"
echo "Node list: $SLURM_NODELIST"
echo "Hostname: $(hostname)"
echo "CPUs per task: $SLURM_CPUS_PER_TASK"
echo "Memory per node: $SLURM_MEM_PER_NODE"

# Set up log file for this specific node
node_log="job_${SLURM_JOBID}_node_${node_id}.log"
echo "Starting simulations on node $node_id at $(date)" > "$node_log"

# Function to log messages
log_message() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message" | tee -a "$node_log"
}

# Initialize process tracking
declare -i process_count=0
declare -i completed_count=0
declare -i failed_count=0
max_processes=12  # Maximum processes per node

# Function to safely get memory usage
get_memory_usage() {
    local pid=$1
    if ps -p $pid > /dev/null 2>&1; then
        local mem_usage=$(ps -o rss= -p $pid 2>/dev/null | awk '{printf "%.2f", $1/1024}')
        if [ -n "$mem_usage" ]; then
            echo "$mem_usage"
            return 0
        fi
    fi
    echo "0.00"
    return 1
}

# Function to monitor memory usage
monitor_memory() {
    local pid=$1
    local city=$2
    local seed=$3
    local max_mem=0
    
    while true; do
        if ! ps -p $pid > /dev/null 2>&1; then
            log_message "Memory monitoring stopped for $city seed $seed (process ended)"
            break
        fi
        
        local mem_usage=$(get_memory_usage $pid)
        if (( $(echo "$mem_usage > $max_mem" | bc -l) )); then
            max_mem=$mem_usage
            log_message "New max memory for $city seed $seed: ${max_mem}MB"
        fi
        
        local available_space=$(df -k . | awk 'NR==2 {print $4}')
        if (( available_space < 1048576 )); then
            log_message "WARNING: Low disk space detected. Stopping memory monitoring."
            break
        fi
        
        sleep 300
    done
}

# Function to wait for processes if we've reached the maximum
wait_for_processes() {
    while (( process_count >= max_processes )); do
        if wait -n; then
            process_count=$((process_count - 1))
            completed_count=$((completed_count + 1))
            log_message "Process completed successfully. Currently running: $process_count processes"
        else
            process_count=$((process_count - 1))
            failed_count=$((failed_count + 1))
            log_message "WARNING: A process failed. Currently running: $process_count processes"
        fi
    done
}

# Function to wait for all remaining processes
wait_for_all_processes() {
    log_message "Waiting for all remaining processes to complete..."
    local remaining=$process_count
    
    while (( remaining > 0 )); do
        if wait -n; then
            remaining=$((remaining - 1))
            completed_count=$((completed_count + 1))
            log_message "Process completed successfully. Remaining: $remaining processes"
        else
            remaining=$((remaining - 1))
            failed_count=$((failed_count + 1))
            log_message "WARNING: A process failed. Remaining: $remaining processes"
        fi
    done
    
    return 0
}

# Function to check if a process is stuck
check_process_health() {
    local pid=$1
    local start_time=$2
    local timeout=7200  # 2 hours timeout
    
    if ! ps -p $pid > /dev/null 2>&1; then
        return 1  # Process died
    fi
    
    local current_time=$(date +%s)
    local runtime=$((current_time - start_time))
    
    if (( runtime > timeout )); then
        log_message "WARNING: Process $pid has been running for more than 2 hours"
        return 2  # Process stuck
    fi
    
    return 0  # Process healthy
}

# Function to monitor process health
monitor_process() {
    local pid=$1
    local city=$2
    local seed=$3
    local start_time=$(date +%s)
    
    log_message "Process health monitoring started for $city seed $seed (PID: $pid)"
    
    while true; do
        check_process_health $pid $start_time
        local status=$?
        
        case $status in
            1)
                log_message "Process $pid for $city seed $seed has terminated"
                break
                ;;
            2)
                log_message "WARNING: Process $pid for $city seed $seed appears to be stuck"
                kill -9 $pid
                break
                ;;
        esac
        
        sleep 300
    done
}

# Function to check disk space
check_disk_space() {
    local required_space=1048576  # 1GB in KB
    local available_space=$(df -k . | awk 'NR==2 {print $4}')
    
    if (( available_space < required_space )); then
        log_message "ERROR: Insufficient disk space. Required: 1GB, Available: $((available_space/1024))MB"
        return 1
    fi
    return 0
}

# Function to verify Java process started successfully
verify_java_process() {
    local pid=$1
    local city=$2
    local seed=$3
    local timeout=30  # 30 seconds to verify process
    
    local start_time=$(date +%s)
    while (( $(date +%s) - start_time < timeout )); do
        if ! ps -p $pid > /dev/null 2>&1; then
            log_message "ERROR: Java process for $city seed $seed failed to start"
            return 1
        fi
        
        # Check if process is actually using CPU
        local cpu_usage=$(ps -o %cpu= -p $pid 2>/dev/null)
        if [ -n "$cpu_usage" ] && (( $(echo "$cpu_usage > 0" | bc -l) )); then
            log_message "Java process for $city seed $seed started successfully"
            return 0
        fi
        
        sleep 5
    done
    
    log_message "ERROR: Java process for $city seed $seed not using CPU after $timeout seconds"
    return 1
}

# Function to monitor CPU usage
monitor_cpu() {
    local pid=$1
    local city=$2
    local seed=$3
    
    while true; do
        if ! ps -p $pid > /dev/null 2>&1; then
            log_message "CPU monitoring stopped for $city seed $seed (process ended)"
            break
        fi
        
        local cpu_usage=$(ps -o %cpu= -p $pid 2>/dev/null)
        if [ -n "$cpu_usage" ]; then
            log_message "CPU usage for $city seed $seed: ${cpu_usage}%"
        fi
        
        sleep 300
    done
}

# Function to rotate logs if they get too large
rotate_logs() {
    local log_size=$(stat -c %s "$node_log" 2>/dev/null || stat -f %z "$node_log")
    local max_size=$((100 * 1024 * 1024))  # 100MB
    
    if (( log_size > max_size )); then
        local timestamp=$(date '+%Y%m%d_%H%M%S')
        mv "$node_log" "${node_log}.${timestamp}"
        echo "Starting new log file at $(date)" > "$node_log"
        log_message "Rotated log file due to size limit"
    fi
}

# Process each city one at a time
for city in "${cities[@]}"; do
    log_message "Starting simulations for city: $city"
    
    # Check disk space before starting new city
    if ! check_disk_space; then
        log_message "ERROR: Not enough disk space to process $city"
        exit 1
    fi
    
    # Calculate start and end seeds for this node
    total_seeds=12
    seeds_per_node=$((total_seeds / 4))  # Fixed to 4 nodes
    start_seed=$((node_id * seeds_per_node + 1))
    end_seed=$((start_seed + seeds_per_node - 1))
    
    log_message "Node $node_id will process seeds $start_seed to $end_seed for $city"
    
    # Run simulations for this city's assigned seeds
    for ((seed=start_seed; seed<=end_seed; seed++)); do
        wait_for_processes
        
        # Check disk space before starting new process
        if ! check_disk_space; then
            log_message "ERROR: Not enough disk space to start new process"
            exit 1
        fi
        
        log_message "Starting simulation for $city with seed $seed"
        java -cp bavaria/target/bavaria-1.5.0.jar org.eqasim.bavaria.RunSimulationsMultipleSeeds \
            --city $city \
            --seeds $seed \
            --threads 4 \
            --memory 6 >> "$node_log" 2>&1 &
        
        sim_pid=$!
        
        # Verify Java process started successfully
        if ! verify_java_process $sim_pid "$city" "$seed"; then
            log_message "ERROR: Failed to start simulation for $city seed $seed"
            exit 1
        fi
        
        # Start health monitoring
        monitor_process $sim_pid "$city" "$seed" &
        
        # Start memory monitoring
        monitor_memory $sim_pid "$city" "$seed" &
        
        # Start CPU monitoring
        monitor_cpu $sim_pid "$city" "$seed" &
        
        process_count=$((process_count + 1))
        log_message "Launched process for $city with seed $seed (Process count: $process_count)"
        
        # Check log size periodically
        rotate_logs
    done
    
    # Wait for all processes for this city to complete
    if wait_for_all_processes; then
        log_message "All simulations completed for $city"
        log_message "Summary for $city:"
        log_message "  Completed: $completed_count"
        log_message "  Failed: $failed_count"
        
        if (( failed_count > 0 )); then
            log_message "ERROR: Some simulations failed for $city"
            exit 1
        fi
    else
        log_message "ERROR: Failed to complete all simulations for $city"
        exit 1
    fi
    
    # Reset counters for next city
    process_count=0
    completed_count=0
    failed_count=0
done

log_message "All cities completed successfully"
exit 0