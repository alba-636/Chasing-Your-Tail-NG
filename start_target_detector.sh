#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Start Target Detector
/usr/bin/python3 $SCRIPT_DIR/src/target_detector.py --config-path $SCRIPT_DIR/config/config.json
