#!/bin/bash
#
# This script sends a signal (raises a flag) to the altimeter
# agent process, telling the process to set the altimeter to
# the current barometric pressure.
#
# Note: the following line must be added to the /etc/sudoers
# file so that the www-data user can start this as a process.
# 
#    www-data ALL=(ALL) NOPASSWD: /home/pi/bin/altimeterReset.sh
#
echo resetting altimeter...

touch /tmp/altimeter/resetAltimeter

