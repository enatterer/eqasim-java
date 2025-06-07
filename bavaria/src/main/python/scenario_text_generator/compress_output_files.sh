for hex in */; do
    cd "$hex" || continue
    hex_name="compressed_${hex%/}"
    mkdir -p "$hex_name"
    for d in */; do
        dir_name="${d%/}"
        # Skip the hex_name directory itself
        if [ "$dir_name" = "$hex_name" ]; then
            continue
        fi
        tar czf "$hex_name/${dir_name}.tar.gz" -C "$dir_name" .
        echo "Compressed $dir_name into $hex_name/${dir_name}.tar.gz"
    done
    cd ..
done


'''
in the $SCRATCH directory, you will find a file called script.sh
'''
#first : copy this script in the city directory, e.g. Bamberg
#second : chmod +x script.sh 
#third : ./script.sh
#fourth : check the compressed files in the city directory, e.g. Bamberg