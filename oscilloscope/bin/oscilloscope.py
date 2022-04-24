#!/usr/bin/python3 -u

# Script: oscilloscope.py
#
# Description:
# This script acquires data from the ADS1115 analog to
# digital converter I2C device and writes the data to the
# output data file.
#
# Note: the following line must be added to the /etc/sudoers
# file so that the www-data user can start this script as a process.
# 
#    www-data ALL=(ALL) NOPASSWD: /home/pi/bin/oscilloscope.py
#
# Copyright 2021 Jeff Owrey
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/license.
#
# Revision History
#   * v10 released 12 Dec 2021 by J L Owrey; first release
#
#12345678901234567890123456789012345678901234567890123456789012345678901234567890

import os
import sys
import math
import psutil
import signal
import time
import json

   ### ENVIRONMENT ###

# get the user running this script
_USER = os.environ['USER']
# html document root directory
_DOCROOT_DIRECTORY = '/home/%s/public_html/oscilloscope/' % _USER
# data from the mpl3115a2 sensor for use by html documents
_OUTPUT_DATA_FILE = _DOCROOT_DIRECTORY + 'dynamic/adcData.js'

    ### GLOBAL CONSTANTS ###

_MAXIMUM_SAMPLE_RATE = 1000 # samples per second
_DEFAULT_SAMPLE_RATE = 1000 # samples per second
_DEFAULT_SAMPLE_SIZE = 200 # number of samples in sample set

    ### GLOBAL VARIABLES ###

sampleSize = _DEFAULT_SAMPLE_SIZE
sampleRate = _DEFAULT_SAMPLE_RATE

# House keeping items
debugMode = False
killAllInstances = False

# Declare global pointer to ADC object.
adc1 = None

def getSamples(sampleSize):
    """
    Description:
    Collects a set of digitized samples from the analog to digital converter.

    Parameters:
        sampleSize - number of samples to collect
    Returns: a list containing the samples
    """
    global sampleRate

    # The sample period tSample must be determined emperically by
    # measuring the time tRead reguired to read a sample from the
    # ADC. To get the sample period add a small guard time before
    # reading the next sample from the ADC.
    #
    # |<----tSample----->|
    # |                  |
    # |<--tRead-->|      |
    # |___________|______|___________ ______ ___
    # X___________X______X___________X______X___
    #       |        |        |
    #       |        |        + next sample read from ADC
    #       |        |
    #       |        +--- guard time between samples
    #       |
    #       +--- read sample from ADC
    #
    if sampleRate > _MAXIMUM_SAMPLE_RATE:
        sampleRate = _MAXIMUM_SAMPLE_RATE
    tSample = 1.0 / sampleRate


    lSamples = []
    lPtr = 0
    previousTime = time.time()
    time_init = previousTime
    while True:
        currentTime = time.time()
        # Note that sampleRate, mentioned in the comment above, 
        # implemented, in this module, by the hardcoded constant
        # _SAMPLE_RATE, determines the maximum ADC sampling rate.
        if currentTime - previousTime > tSample: 
            previousTime = currentTime
            if lPtr == sampleSize:
                if debugMode:
                    time_acq = time.time() - time_init
                    rate = time_acq / sampleSize
                    print('t_acq: %.6f  rate: %.8f' % \
                          (time_acq, rate))
                return lSamples         
            lSamples.append(adc1.getVoltage())
            lPtr += 1

            elapsedTime = time.time() - currentTime
            remainingTime = tSample - elapsedTime - 0.001
            if remainingTime > 0.0:
                time.sleep(remainingTime)
        ## end if
    ## end while
## end def

def convertData(lSamples, dData):
    """
    Description:
    Formats the sample data and stores the sample data in a dictionary
    object in preparation for being written to the output data file.

    Parameters:
        lSamples - a list containing the samples from the ADC
        dData - a dictionary containing the samples and additional info
    Returns: True if successful, False otherwise
    """  
    sampleSize = len(lSamples)
    sampleSizeMinus1 = sampleSize - 1
    sData = ''
    for i in range(sampleSizeMinus1):
        sData += '%.3f, ' % lSamples[i]
    sData += '%.3f' % lSamples[sampleSizeMinus1]
    dData['rate'] = sampleRate
    dData['size'] = sampleSize
    dData['samples'] = sData
    return True
## end def

def writeOutputDataFile(dData):
    """
    Description:
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

    # Create a JSON formatted string from the sensor data.
    jsData = json.loads("{}")
    try:
        jsData.update({'rate':dData['rate']})
        jsData.update({'size':dData['size']})
        jsData.update({'samples':dData['samples']})
        sData = "[%s]" % json.dumps(jsData)
    except Exception as exError:
        print("writeOutputFile: %s" % (exError))
        return False

    if debugMode and False:
        print(sData)

    # Write the JSON formatted data to the output data file.

    try:
        fc = open(_OUTPUT_DATA_FILE, "w")
        fc.write(sData)
        fc.close()
    except Exception as exError:
        print("write output file failed: %s" % \
              (exError))
        return False

    return True
##end def

def terminateProcess(signal, frame):
    """
    Description:
    Informs downstream clients that this process has been
    terminiated.  Downstream clients are informed by removing
    the output data file.

    Parameters:
       signal, frame - dummy parameters
    Returns: nothing
    """
    # Inform downstream clients by removing output data file.
    if os.path.exists(_OUTPUT_DATA_FILE):
        os.remove(_OUTPUT_DATA_FILE)
    if debugMode:
        print()
    sys.exit(0)
##end def

def killOtherInstances():
    """
    Description:
    Allows only one instance to run at a time to avoid
    possible smbus bus contention.

    Parameters: none
    Returns: nothing
    """
    thisProc = os.path.basename(__file__)

    # Get the list of currently running processes that have the same
    # name as this process, i.e., have the name "fncgen.py".
    lProcs = []
    for proc in psutil.process_iter():
        if proc.name() == thisProc:
            lProcs.append(proc)
    # Remove the most recently instantiated instance of this process
    # from the list.
    lProcs = lProcs[:-1]
    # Kill all previously instantiated instances.
    for proc in lProcs:
        os.kill(proc.pid, signal.SIGTERM)
## end def

def getCLarguments():
    """
    Description:
    Get the following command line arguments

    Usage: adcacq.py [-r sample rate] [-n number samples] [-d]
    -r  samples per second
    -n  number of samples to acquire per frame
    -k  kill all running instances and exit
    -d  debug mode

    Parameters: none
    Returns: nothing
    """
    global debugMode, sampleSize, sampleRate, killAllInstances

    index = 1
    while index < len(sys.argv):
        if sys.argv[index] == '-n':
            sampleSize = int(sys.argv[index + 1])
            assert sampleSize > 0 and sampleSize < 1001, \
                'invalid sample size'
            index += 1
        elif sys.argv[index] == '-r':
            sampleRate = int(sys.argv[index + 1])
            assert sampleRate > 0, \
                'invalid sample rate'
            index += 1
        elif sys.argv[index] == '-d':
            debugMode = True
        elif sys.argv[index] == '-k':
            killAllInstances = True
        else:
            cmd_name = sys.argv[0].split('/')
            print('Usage: %s [-r sample rate] [-n number samples] '
                  '[-d debug mode]' % cmd_name[-1])
            exit(-1)
        index += 1
    return
## end def

def main():
    """
    Description:
    Instaniates an ADC object and begins collecting samples from the ADC
    and writing the samples to the output data file.

    Parameters: none
    Returns: nothing
    """
    global adc1

    # set the ADC to maximum sampling rate
    #tconfig = 0xC203;
    #tconfig = 0xC283;
    tconfig = 0xC2E3; # maximum sampling rate

    # Register a callback function to cleanup after getting a CTL-C
    # or kill signal.
    signal.signal(signal.SIGTERM, terminateProcess)
    signal.signal(signal.SIGINT, terminateProcess)

    getCLarguments()

    # Kill all other running instances of this program.  Killing
    # other instances prevents possible smbus contention.
    killOtherInstances()

    # Create an instance of the ADC interface layer.
    import ads1115
    adc1 = ads1115.ads1115(config=tconfig, debug=False)

    if killAllInstances:
        terminateProcess(0,0)

    # Begin collecting ADC samples indefinitely.
    while True:
        dSamples = {}
        lSamples = getSamples(sampleSize)
        convertData(lSamples, dSamples)
        writeOutputDataFile(dSamples)
## end def

if __name__ == '__main__':
    main()

## end module
