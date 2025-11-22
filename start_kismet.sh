#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Set wlan1 in monitor mode
/usr/bin/sudo /usr/sbin/airmon-ng start wlan1

# Start kismet
/usr/bin/sudo /usr/bin/kismet --override=$SCRIPT_DIR/config/kismet.conf
