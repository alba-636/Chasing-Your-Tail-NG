#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Start Data Collector
/usr/bin/python3 $SCRIPT_DIR/src/DataCollector.py --config-path $SCRIPT_DIR/config/config.json
