#!/bin/bash

# Set wlan1 in monitor mode
/usr/bin/sudo /usr/sbin/airmon-ng start wlan1

# Start kismet
/usr/bin/sudo /usr/bin/kismet --override=/home/tail/Chasing-Your-Tail-NG/config/kismet.conf
