#!/bin/bash

#SBATCH -J simulation_basecases_multiple_nodes

# Output and error files
#SBATCH --output=simulation_basecases_multiple_nodes_output_%j.log
#SBATCH --error=simulation_basecases_multiple_nodes_error_%j.log

#SBATCH --nodes=4
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=12
#SBATCH --mem=80GB
#SBATCH --time=48:00:00

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

# Get the working directory where the job was submitted from
WORK_DIR="$SLURM_SUBMIT_DIR"
if [ -z "$WORK_DIR" ]; then
    WORK_DIR="$(pwd)"
fi

# Define the node-specific script with full path
NODE_SCRIPT="${WORK_DIR}/simulation_node.sbatch"

# Verify the node script exists
if [ ! -f "$NODE_SCRIPT" ]; then
    echo "Error: Node script not found at $NODE_SCRIPT"
    echo "Current working directory: $WORK_DIR"
    echo "Contents of working directory:"
    ls -la "$WORK_DIR"
    exit 1
fi

# Submit 4 separate jobs, one for each node
for node_id in {0..3}; do
    echo "Submitting job for node $node_id"
    sbatch \
        --job-name="sim_node_${node_id}" \
        --output="simulation_node_${node_id}_%j.log" \
        --error="simulation_node_${node_id}_%j.err" \
        --nodes=1 \
        --ntasks-per-node=4 \
        --cpus-per-task=12 \
        --mem=80GB \
        --time=48:00:00 \
        --account=pn39mu \
        --partition=micro \
        --export=ALL,NODE_ID=${node_id} \
        --chdir="$WORK_DIR" \
        "$NODE_SCRIPT"
done

echo "All jobs submitted. Check their status with: squeue -u $USER"