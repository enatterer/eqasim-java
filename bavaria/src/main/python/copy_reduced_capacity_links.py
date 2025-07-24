import os
import shutil

#cities_1=['nuernberg', 'augsburg', 'muenchen','schweinfurt', 'aschaffenburg', 'wuerzburg', 'bamberg', 'bayreuth', 'erlangen', 'fuerth', 'kempten','landshut', 'ingolstadt', 'regensburg', 'neuulm',rosenheim]

cities = ["augsburg","nuernberg","muenchen","schweinfurt","aschaffenburg","wuerzburg","bamberg","bayreuth","erlangen","fuerth","kempten","landshut","ingolstadt","regensburg","neuulm"]
hex_sizes = [500]

for city in cities:
    for hex_size in hex_sizes:
        source_dir = f"/hppfs/work/pn39mu/go69tef3/eqasim_bavaria/bavaria/data/subgraph/network_files/{city}/{city}_seed_3_hex{hex_size}_mean4_std8/networks"
        target_dir = f"/hppfs/work/pn39mu/go69tef3/eqasim_bavaria/bavaria/data/reduced_capacity_edges/{city}/{city}_hex_{hex_size}_seed_3"
        
        os.makedirs(target_dir, exist_ok=True)

        for filename in os.listdir(source_dir):
            if filename.endswith("_reduced_capacity_edges.geojson"):
                src_path = os.path.join(source_dir, filename)
                dst_path = os.path.join(target_dir, filename)
                shutil.copy2(src_path, dst_path)  # copy2 preserves metadata
                print(f"Copied: {filename}")