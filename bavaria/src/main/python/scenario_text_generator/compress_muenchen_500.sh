#!/bin/bash

# Script to compress muenchen_hex_500_seed_2 directory excluding output_events.xml.gz
# Usage: ./compress_muenchen_500.sh

# Set the specific directory to process
HEX_DIR="muenchen_hex_500_seed_2"

# Check if the directory exists
if [ ! -d "$HEX_DIR" ]; then
    echo "Error: Directory $HEX_DIR not found!"
    exit 1
fi

echo "Starting compression for $HEX_DIR..."
echo "=========================================="

# Change to the hex directory
cd "$HEX_DIR" || exit 1

# Set up directory names
old_hex_name="compressed_${HEX_DIR}"
new_hex_name="no_events_compressed_${HEX_DIR}"

# Create the compressed directory
mkdir -p "$new_hex_name"

echo "Processing directory: $HEX_DIR"
echo "Creating compressed files in: $new_hex_name"

# Loop through all subdirectories
for d in */; do
    dir_name="${d%/}"
    
    # Skip the compressed directories themselves
    if [ "$dir_name" = "$old_hex_name" ] || [ "$dir_name" = "$new_hex_name" ]; then
        echo "Skipping compressed directory: $dir_name"
        continue
    fi
    
    # Check if this is a network directory (contains output_events.xml.gz)
    if [ -f "$dir_name/output_events.xml.gz" ]; then
        # This is a network directory, compress its contents excluding output_events.xml.gz
        tar --exclude="output_events.xml.gz" -czf "$new_hex_name/${dir_name}.tar.gz" -C "$dir_name" .
        echo "✓ Compressed contents of $dir_name into $new_hex_name/${dir_name}.tar.gz (excluding output_events.xml.gz)"
    else
        # This is not a network directory, compress it normally
        tar -czf "$new_hex_name/${dir_name}.tar.gz" -C "$dir_name" .
        echo "✓ Compressed $dir_name into $new_hex_name/${dir_name}.tar.gz"
    fi
done

# Go back to parent directory
cd ..

echo "=========================================="
echo "Compression completed for $HEX_DIR!"
echo "Compressed files are in: $HEX_DIR/$new_hex_name/" 