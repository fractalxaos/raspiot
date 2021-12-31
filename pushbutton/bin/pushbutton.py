#!/usr/bin/python3 -u
#
# This python program reads a GPIO digital input connected to a
# push button switch and prints out the number of times the
# button has been pushed.
#
# Note: the following line must be added to the /etc/sudoers
# file so that the www-data user can start this as a process.
# 
#    www-data ALL=(ALL) NOPASSWD: /home/pi/bin/pushbutton.py
#
# Circuit:
#   SPST momentary closed switch: pin 1 of switch connected
#   to VCC. Pin 2 connected to digital GPIO pin and to a 10K
#   Ohm resister.  Other end of the resister connected to GND.
#   Pushing the button sends a HIGH logic level to the
#   raspberry pi, otherwise the level is LOW.
#
# Revision History
#   * v10 released 12 Dec 2021 by J L Owrey; first release
#
#12345678901234567890123456789012345678901234567890123456789012345678901234567890

    ### IMPORTS ###

import os
import signal
import sys
import time
import json
import RPi.GPIO as GPIO

    ### ENVIRONMENT ###

_USER = os.environ['USER']

    ### FILE AND FOLDER LOCATIONS ###

# folder to contain html
_DOCROOT_PATH = "/home/%s/public_html/pushbutton/" % _USER
# location of JSON output data file
_OUTPUT_DATA_FILE = _DOCROOT_PATH + "dynamic/pushButtonData.js"

    ### GLOBAL CONSTANTS ###

# Define the GPIO pin the button uses.
_PUSH_BUTTON_GPIO_PIN = 5
# Set the time required to debounce the push button.
_DEFAULT_DEBOUNCE_TIME = 200 # milliseconds

    ### GLOBAL VARIABLES ###

# Initialize a variable for counting button pushes.
count = 0
# Amount of time for the push button to "debounce".
debounceTime = _DEFAULT_DEBOUNCE_TIME

# turns on or off extensive debugging messages
verboseMode = False

    ### INTERRUPT HANDLERS ###

# Interrupt routine called when the button is pressed.
def buttonPress(channel):
    """
    Handles push button press events. Increments a counter each time
    the button gets pressed and updates the output data file used by 
    web clients.
    """
    global count
    count += 1
    writeOutputFile()
## end def    

    ### HELPER ROUTINES ###

def getTimeStamp():
    """
    Get the local time and format as a text string.
    Parameters: none
    Returns: string containing the time stamp
    """
    return time.strftime( "%m/%d/%Y %T", time.localtime() )
## end def

def terminateProcess(signal, frame):
    """When the this process gets killed by the operating system,
       inform downstream clients by removing the output data file.
       Parameters:
           signal, frame - dummy parameters
       Returns: nothing
    """
    # Inform downstream clients by removing output data file.
    if os.path.exists(_OUTPUT_DATA_FILE):
       os.remove(_OUTPUT_DATA_FILE)
    print();
    sys.exit(0)
##end def

    ### PUBLIC FUNCTIONS ###

def writeOutputFile():
    """
    Write sensor data items to the output data file, formatted as 
    a Javascript file.  This file may then be requested and used by
    by downstream clients, for instance, an HTML document.
    Parameters:
        dData - a dictionary containing the data to be written
                   to the output data file
        Returns: True if successful, False otherwise
    """
    # Write a JSON formatted file for use by html clients.  The following
    # data items are sent to the client file.
    #    * The last database update date and time
    #    * The data request interval
    #    * The sensor values

    # Create a JSON formatted string from the sensor data.
    dData = {}
    dData['time'] = getTimeStamp()
    dData['count'] = str(count)

    jsData = json.loads("{}")
    try:
        for key in dData:
            jsData.update({key:dData[key]})
        sData = "[%s]" % json.dumps(jsData)
    except Exception as exError:
        print("%s writeOutputFile: %s" % (getTimeStamp(), exError))
        return False

    if verboseMode:
        print(sData)

    # Write the JSON formatted data to the output data file.
    try:
        fc = open(_OUTPUT_DATA_FILE, "w")
        fc.write(sData + '\n')
        fc.close()
    except Exception as exError:
        print("%s write output file failed: %s" % \
              (getTimeStamp(), exError))
        return False

    return True
## end def

def getCLarguments():
    """
    Get command line arguments.  There are three possible arguments
        -d turns on debug mode
        -v turns on verbose mode
        -b sets switch debounce time
    Returns: nothing
    """
    global verboseMode, debounceTime

    index = 1
    while index < len(sys.argv):
        if sys.argv[index] == '-v':
            verboseMode = True
        elif sys.argv[index] == '-b':
            try:
                debounceTime = abs(float(sys.argv[index + 1]))
            except:
                print("invalid debounce time")
                exit(-1)
            index += 1
        else:
            cmd_name = sys.argv[0].split('/')
            print("Usage: %s [-v] [-b seconds]" \
                  % cmd_name[-1])
            exit(-1)
        index += 1
##end def

    ### MAIN ROUTINE ###

def main():
    # Register callback function to do cleanup housekeeping
    # if this script terminated by CTL-c or by kill signal.
    signal.signal(signal.SIGTERM, terminateProcess)
    signal.signal(signal.SIGINT, terminateProcess)

    # Get command line arguments.
    getCLarguments()

    # Initialize the GPIO interface.
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Setup as input the pin used for the push button.
    #GPIO.setup(_PUSH_BUTTON_GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(_PUSH_BUTTON_GPIO_PIN, GPIO.IN)

    # Add an interrupt handler to process button pushes.
    GPIO.add_event_detect(_PUSH_BUTTON_GPIO_PIN, GPIO.RISING,
                          callback=buttonPress,
                          bouncetime=debounceTime) 

    # Initialize output data file.
    writeOutputFile()

    # Script will run forever or until interrupted CTL-C or kill signal.
    while True:
        time.sleep(0.5)
    ## end while
## end def

if __name__ == '__main__':
    main()

# end module

