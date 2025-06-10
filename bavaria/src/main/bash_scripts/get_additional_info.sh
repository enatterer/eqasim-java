#!/bin/bash
# List of cities, seeds, and hex sizes
cities=("rosenheim")  # <-- Replace with your actual city names
seeds=(1)             # <-- Replace with your actual seeds
hex_sizes=(500 1000 2000)
mean_factor=4
std_factor=8

# Base directories
data_dir="$(pwd)/bavaria/data"
subgraph_dir="$data_dir/subgraph"
output_base="$data_dir/additional_info"

for city in "${cities[@]}"; do
  for seed in "${seeds[@]}"; do
    for hex in "${hex_sizes[@]}"; do
      # Find all matching network directories
      for netdir in $subgraph_dir/network_files/$city/${city}_seed_${seed}_hex${hex}_mean${mean_factor}_std${std_factor}/networks/; do
        # Skip if no such directory
        [ -d "$netdir" ] || continue

        # Prepare output directory
        outdir="$output_base/$city/${city}_hex_${hex}_seed_${seed}_mean${mean_factor}_std${std_factor}"
        mkdir -p "$outdir"

        # Copy .geojson and .json files
        find "$netdir" -maxdepth 1 -type f \( -name "*.geojson" -o -name "*.json" \) -exec cp {} "$outdir" \;

        echo "Copied files for $city, seed $seed, hex $hex to $outdir"
      done
    done
  done
done