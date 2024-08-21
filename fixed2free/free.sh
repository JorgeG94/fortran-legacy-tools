#!/bin/bash

# List of files to skip
# these are the cursed files that should stay in f77
skip_files=("tddxcd_m05.src" "tddxcd_m06.src" "dftgrd.src" "dftxcc.src"
            "dftxcg.src" "dftxcb.src" "dftxca.src" "dftxcf.src" "dftxcd.src"
            "dftxce.src")
# Check if the newfixed2free2.py script is available
if ! [[ -f "./fixed2free2.py" ]]; then
    echo "Error: fixed2free2.py script not found!"
    exit 1
fi

# Iterate over all *.src files
for file in *.src; do
    # Skip files in the skip_files array
    if [[ " ${skip_files[@]} " =~ " ${file} " ]]; then
        continue
    fi

    # Define backup file name
    backup_file="${file%.*}_backup.src"

    # Backup the original file
    cp "$file" "$backup_file"

    # Convert from fixed to free format using fixed2free2.py with in-place editing
    ./fixed2free2.py "$file" --inplace

done
