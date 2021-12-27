#!/bin/sh
# Put commands here to start up things everytime the Raspberry Pi
# boots up.

# Create a directory in tmpfs for altimeter data.
mkdir /tmp/altimeter
sudo chown :www-data /tmp/altimeter
chmod g+w /tmp/altimeter

# Create a directory in tmpfs for oscilloscope data.
mkdir /tmp/oscilloscope
sudo chown :www-data /tmp/oscilloscope
chmod g+w /tmp/oscilloscope

# Create a directory in tmpfs for push button data.
mkdir /tmp/pushbutton
sudo chown :www-data /tmp/pushbutton
chmod g+w /tmp/pushbutton

# Start altimeter agent
(sleep 5; /home/pi/bin/altstart;) &

# Blink LED to show boot process complete
/home/pi/bin/blinkLed.sh
