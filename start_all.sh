#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

scripts=("$SCRIPT_DIR/start_kismet.sh" "$SCRIPT_DIR/target_detector.sh")

for script in scripts; do
    echo "$script"
fi
done | xargs -P 2 -I {} /bin/bash "{}"
