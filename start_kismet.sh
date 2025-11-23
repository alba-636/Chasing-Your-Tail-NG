#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Start kismet
/usr/bin/sudo /usr/bin/kismet --override=$SCRIPT_DIR/config/kismet.conf
