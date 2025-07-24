#!/bin/bash

# Script to copy compressed files from scratch to DSS storage
# Usage: ./copy_compressed_files.sh

# Source and destination base paths
SCRATCH_BASE="/hppfs/scratch/05/go69tef3/bavaria_simulation_output"
DSS_BASE="/dss/dssfs03/pn39mu/pn39mu-dss-0000/bavaria_simulations/simulation_output"

# Cities to process (excluding muenchen as requested earlier)
CITIES=("augsburg")

# Hexagon sizes
HEX_SIZES=("500" "1000" "2000")

# Seed number
SEED="2"

echo "Starting to copy compressed files from scratch to DSS storage..."
echo "Source: $SCRATCH_BASE"
echo "Destination: $DSS_BASE"
echo "Cities: ${CITIES[*]}"
echo "Hexagon sizes: ${HEX_SIZES[*]}"
echo "Seed: $SEED"
echo "=========================================="

# Loop through each city
for city in "${CITIES[@]}"; do
    echo "Processing city: $city"
    
    # Destination directory (already exists)
    DEST_DIR="$DSS_BASE/$city"
    
    # Loop through each hexagon size
    for hex_size in "${HEX_SIZES[@]}"; do
        # Source directory structure: city/hex_dir/compressed_dir
        HEX_DIR_NAME="${city}_hex_${hex_size}_seed_${SEED}"
        SRC_DIR_NAME="no_events_compressed_${city}_hex_${hex_size}_seed_${SEED}"
        SRC_PATH="$SCRATCH_BASE/$city/$HEX_DIR_NAME/$SRC_DIR_NAME"
        
        # Check if source directory exists
        if [ -d "$SRC_PATH" ]; then
            echo "  Copying $SRC_DIR_NAME..."
            cp -r "$SRC_PATH" "$DEST_DIR/"
            if [ $? -eq 0 ]; then
                echo "  ✓ Successfully copied $SRC_DIR_NAME"
            else
                echo "  ✗ Failed to copy $SRC_DIR_NAME"
            fi
        else
            echo "  ⚠ Source directory not found: $SRC_PATH"
        fi
    done
    echo "------------------------------------------"
done

echo "=========================================="
echo "Copy operation completed!"
echo "Summary:"
echo "  - Processed ${#CITIES[@]} cities"
echo "  - Each city has ${#HEX_SIZES[@]} hexagon sizes"
echo "  - Total expected copies: $((${#CITIES[@]} * ${#HEX_SIZES[@]}))"