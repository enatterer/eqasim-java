for hex in */; do
    cd "$hex" || continue
    old_hex_name="compressed_${hex%/}"
    new_hex_name="no_events_compressed_${hex%/}"
    mkdir -p "$new_hex_name"
    for d in */; do
        dir_name="${d%/}"
        # Skip the compressed directories themselves
        if [ "$dir_name" = "$old_hex_name" ] || [ "$dir_name" = "$new_hex_name" ]; then
            continue
        fi
        
        # Check if this is a network directory (contains output_events.xml.gz)
        if [ -f "$dir_name/output_events.xml.gz" ]; then
            # This is a network directory, compress its contents excluding output_events.xml.gz
            tar --exclude="output_events.xml.gz" -czf "$new_hex_name/${dir_name}.tar.gz" -C "$dir_name" .
            echo "Compressed contents of $dir_name into $new_hex_name/${dir_name}.tar.gz (excluding output_events.xml.gz)"
        else
            # This is not a network directory, compress it normally
            tar -czf "$new_hex_name/${dir_name}.tar.gz" -C "$dir_name" .
            echo "Compressed $dir_name into $new_hex_name/${dir_name}.tar.gz"
        fi
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