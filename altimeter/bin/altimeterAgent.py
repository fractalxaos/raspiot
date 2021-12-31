#!/usr/bin/python3 -u
## The -u option turns off block buffering of python output. This assures
## that error messages get printed to the log file as they happen.
#  
# Module: mpl3115a2_agent.py
#
# Description: This module acts as an agent between the MPL3115 sensor and
# the web services.  The agent
#     - converts units of various sensor data items
#     - updates a round robin (rrdtool) database with the sensor data
#     - periodically generate graphic charts for display in html documents
#     - writes the processed sensor data to a JSON file for use by
#       html documents
#
# Note: _rrdtool_ must be installed on the host running this program.
#
# Install rrdtool on the raspberry pi by running
#
#     sudo apt-get install rrdtool
# 
# Create a directory /home/$USER/database for the rrdtool database.
# For more information on rrdtool see http://oss.oetiker.ch/rrdtool
#       
# Copyright 2018 Jeff Owrey
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
#    You should have received a copy of the GNU General Public Licensef
#    along with this program.  If not, see http://www.gnu.org/license.
#
# Revision History
#   * v10 - 12 Dec 2021 by J L Owrey; first release

import os
import sys
import signal
import subprocess
import multiprocessing
import time
import json
import rrdbase
import mpl3115

    ### FILE AND FOLDER LOCATIONS ###

# get the user running this script
_USER = os.environ['USER']
# html document root directory
_DOCROOT_DIRECTORY = '/home/%s/public_html/altimeter/' % _USER
# location of charts used by html documents
_CHARTS_DIRECTORY = _DOCROOT_DIRECTORY + 'dynamic/'
# data from the mpl3115a2 sensor for use by html documents
_OUTPUT_DATA_FILE = _DOCROOT_DIRECTORY + 'dynamic/altimeterData.js'
# rrdtool database file
_RRD_FILE = '/home/%s/database/altimeterData.rrd' % _USER
# altimeter reset signal file - created by user action
_ALTIMETER_RESET_FILE = "/tmp/altimeter/resetAltimeter"

    ### GLOBAL CONSTANTS ###

# web page data item refresh rate (sec)
_SENSOR_POLLING_INTERVAL = 5
# rrdtool database update rate (sec)
_DATABASE_UPDATE_INTERVAL = 30
# max number of failed attempts to get sensor data
_MAX_FAILED_DATA_REQUESTS = 3

# generation rate of day charts (sec)
_CHART_UPDATE_INTERVAL = 300
# standard chart width in pixels
_CHART_WIDTH = 600
# standard chart height in pixels
_CHART_HEIGHT = 150

# i2c smbus device address
_ALT_SENSOR_ADDR = 0x60
_BUS_NUMBER = 1

   ### CONVERSION FACTORS ###

# inches Hg per Pascal
_PASCAL_CONVERSION_FACTOR = 0.29530099194
# filters out unwanted noise from pressure sensor
_MAX_ALLOWED_PRESSURE_SPIKE = 0.34

   ### GLOBAL VARIABLES ###

# turns on or off extensive debugging messages
debugMode = False
verboseMode = False

# rate at which data retrieved from sensors
sensorPollingInterval = _SENSOR_POLLING_INTERVAL
# number of failed attempts to get sensor data
failedUpdateCount = 0
# sensor status
sensorOnline = False
# filters out unwanted noise from pressure sensor
currentPressure = 0

# altimeter sensor object
alt1 = None
# rrdtool database handler instance
rrdb = None

    ### HELPER FUNCTIONS ###

def getTimeStamp():
    """
    Description:
    Sets the error message time stamp to the local system time.

    Parameters: none
    Returns: string containing the time stamp.
    """
    return time.strftime('%m/%d/%Y %H:%M:%S', time.localtime())
##end def

def getEpochSeconds(sTime):
    """
    Description:
    Convert the time stamp supplied in the sensor data string
    to seconds since 1/1/1970 00:00:00.

    Parameters: 
       sTime - the time stamp to be converted must be formatted
               as %m/%d/%Y %H:%M:%S
    Returns: epoch seconds.
    """
    try:
        t_sTime = time.strptime(sTime, '%m/%d/%Y %H:%M:%S')
    except Exception as exError:
        print('%s getEpochSeconds: %s' % (getTimeStamp(), exError))
        return None
    tSeconds = int(time.mktime(t_sTime))
    return tSeconds
##end def

def setStatusToOffline():
    """
    Description: Set the detected status of the sensor to
    "offline" and inform downstream clients by removing input
    and output data files.

    Parameters: none
    Returns: nothing
    """
    global sensorOnline

    # Inform downstream clients by removing output data file.
    if os.path.exists(_OUTPUT_DATA_FILE):
       os.remove(_OUTPUT_DATA_FILE)
    # If the sensor or  device was previously online, then send
    # a message that we are now offline.
    if sensorOnline:
        print('%s sensor offline' % getTimeStamp())
    sensorOnline = False
##end def

def terminateAgentProcess(signal, frame):
    """
    Description: 
    Send a message to log when the agent process gets killed
    by the operating system.  Inform downstream clients
    by removing input and output data files.

    Parameters:
        signal, frame - dummy parameters
    Returns: nothing
    """
    print('%s terminating agent process' % getTimeStamp())
    # Inform downstream clients by removing output data file.
    if os.path.exists(_OUTPUT_DATA_FILE):
       os.remove(_OUTPUT_DATA_FILE)
    sys.exit(0)
##end def

    ### PUBLIC FUNCTIONS ###
def checkForAltimeterReset(altitudeSensor):
    """
    Description: 
    Check to see if the user has clicked the Reset Altimeter
    button on the web page.
    Parameters:
        altitudeSensor - MPL3115 class instance object
    Returns: nothing
    """
    if os.path.exists(_ALTIMETER_RESET_FILE):
        # Get current pressure in kPa.
        currentBar = altitudeSensor.getPressure(mode='B')
        # Calibrate for measureing altitude above ground level (AGL)
        print("%s setting altimeter to: %.2f" % \
              (getTimeStamp(), currentBar)) 
        altitudeSensor.setPressureOffset(currentBar, mode='B')
        # Lower altitude reset flag.  When the user clicks the Altitude
        # Reset button, the browser launches a PHP script on the server.
        # This PHP script "raises" a reset flag by calling a server side
        # bash script that writes an empty file to the /tmp/altitude
        # folder.  
        os.remove(_ALTIMETER_RESET_FILE)
## end def

def getSensorData(objSensor, dData):
    """
    Description:
    Gets altitude, pressure, and temperature from the MPL3115A2
    sensor.

    Parameters:
        objSensor - altitude sensor instance object
        dData - a dictionary object to contain sensor data
    Returns: True if successful, False otherwise
    """
    
    # Set date item to current date and time.
    dData['date'] = getTimeStamp()
    dData['chartUpdateInterval'] = str(_CHART_UPDATE_INTERVAL)

    # Get sensor data.
    try:
        dData['tempC'] = objSensor.getTemperature()
        dData['altitude'] = objSensor.getAltitude()
        dData['pressure'] = objSensor.getPressure()
    except Exception as exError:
        dData['status'] = 'offline'
        print('%s getSensorData: %s' % (getTimeStamp(), exError))
        return False

    dData['status'] = 'online'
 
    if verboseMode:
        print("Altitude: %.1f m" % dData['altitude'])
        print("Pressure: %.2f kPa" % dData['pressure'])
        print("Temperature: %.2f C" % dData['tempC'])

    return True
##end def

def convertData(dData):
    """
    Description:
    Convert individual sensor data items as necessary.  Also
    format data items for use by html documents.

    Parameters:
       dData - a dictionary object containing the data items to be
               converted
    Returns: true if successful, false otherwise.
    """
    global currentPressure

    try:
        # Validate altitude data
        altitude = dData['altitude']
        if altitude < -1000.0 or altitude > 20000.0:
            raise Exception('invalid altitude: %.4e' % altitude)
        dData['altitude'] = '%.1f' % altitude

        # Validate pressure data
        pressure = dData['pressure']
        pressureBar = pressure * _PASCAL_CONVERSION_FACTOR
        pDelta = abs(pressure - currentPressure)
        currentPressure = pressure
        if pDelta > _MAX_ALLOWED_PRESSURE_SPIKE:
            raise Exception('invalid pressure: %.4e  pDelta: %s' % \
                             (pressure, pDelta))
        dData['pressure'] = '%.4f' % pressure
        dData['bar'] = '%.4f' % pressureBar

        # Validate temperature data
        tempC = dData['tempC']
        tempF = (9.0/5.0) * tempC + 32.0
        if tempC < -40.0 or tempC > 85.0:
            raise Exception('invalid temperature: %.4e' % tempF)
        dData['tempF'] = '%.2f' % tempF
        dData['tempC'] = '%.2f' % tempC

    except Exception as exError:
        # Trap any data conversion errors.
        print('%s convertData: %s' % (getTimeStamp(), exError))
        return False

    return True
##end def

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
        for key in dData:
            jsData.update({key:dData[key]})
        sData = "[%s]" % json.dumps(jsData)
    except Exception as exError:
        print("%s writeOutputFile: %s" % (getTimeStamp(), exError))
        return False

    if debugMode:
        print(sData)

    # Write the JSON formatted data to the output data file.

    try:
        fc = open(_OUTPUT_DATA_FILE, "w")
        fc.write(sData)
        fc.close()
    except Exception as exError:
        print("%s write output file failed: %s" % \
              (getTimeStamp(), exError))
        return False

    return True
##end def

def setStatus(updateSuccess):
    """
    Description:
    Detect if device is offline or not available on
    the network. After a set number of attempts to get data
    from the device set a flag that the device is offline.

    Parameters:
        updateSuccess - a boolean that is True if data request
                        successful, False otherwise
    Returns: nothing
    """
    global failedUpdateCount, sensorOnline

    if updateSuccess:
        failedUpdateCount = 0
        # Set status and send a message to the log if the device
        # previously offline and is now online.
        if not sensorOnline:
            print('%s sensor online' % getTimeStamp())
            sensorOnline = True
    else:
        # The last attempt failed, so update the failed attempts
        # count.
        failedUpdateCount += 1

    if failedUpdateCount == _MAX_FAILED_DATA_REQUESTS:
        # Max number of failed data requests, so set
        # device status to offline.
        setStatusToOffline()
##end def

    ### DATABASE FUNCTIONS ###

def generateDayGraphs():
    """
    Description:
    Generate graphs for html documents. Calls createGraph for each graph
    that needs to be created.

    Parameters: none
    Returns: nothing
    """
    rrdb.createAutoGraph('1d_altitude', 'altitude', 'meters', \
                         'Altitude', 'now-1d', 0, 0, 0, True)
    rrdb.createAutoGraph('1d_pressure', 'pressure', 'inches\ Hg', \
                         'Barometric\ Pressure', 'now-1d', 0, 0, 0, True)
    rrdb.createAutoGraph('1d_temperature', 'temperature', \
                         'degrees\ Fahrenheit', \
                         'Temperature', 'now-1d', 0, 0, 0, True)
    rrdb.createAutoGraph('10d_altitude', 'altitude', 'meters', \
                         'Altitude', 'end-10days', 0, 0, 0, True)
    rrdb.createAutoGraph('10d_pressure', 'pressure', 'inches\ Hg', \
                         'Barometric\ Pressure', 'end-10days', \
                         0, 0, 0, True)
    rrdb.createAutoGraph('10d_temperature', 'temperature', \
                         'degrees\ Fahrenheit', \
                         'Temperature', 'end-10days', 0, 0, 0, True)
##end def

def getCLarguments():
    """
    Description:
    Get command line arguments. Possible arguments
        -d turns on debug mode
        -v turns on verbose debug mode
        -p sets the sensor polling interval

    Parameters: none
    Returns: nothing
    """
    global debugMode, verboseMode, sensorPollingInterval

    index = 1
    while index < len(sys.argv):
        if sys.argv[index] == '-v':
            verboseMode = True
        elif sys.argv[index] == '-d':
            verboseMode = True
            debugMode = True
        elif sys.argv[index] == '-p':
            try:
                sensorPollingInterval = abs(int(sys.argv[index + 1]))
            except:
                print("invalid polling period")
                exit(-1)
            index += 1
        else:
            cmd_name = sys.argv[0].split('/')
            print('Usage: %s [-v|d] [-p seconds]' % cmd_name[-1])
            exit(-1)
        index += 1
    return
##end def

     ### MAIN ROUTINE ###

def setup():
    """
    Description:
    Executive routine which manages timing and execution of all other
    events.

    Parameters: none
    Returns: nothing
    """
    global currentPressure, rrdb, alt1

    # Register callback function to handle CTL-C or kill signal events.
    signal.signal(signal.SIGTERM, terminateAgentProcess)
    signal.signal(signal.SIGINT, terminateAgentProcess)

    # Log agent process startup time.
    print('%s === starting up altimeter agent process' % \
              getTimeStamp())

    # Get any command line arguments.
    getCLarguments()

    # Create altimeter sensor object.
    alt1 = mpl3115.mpl3115(_ALT_SENSOR_ADDR,
            _BUS_NUMBER, debug=debugMode)

    # Get current pressure in kPa.
    currentPressure = alt1.getPressure()
    # Calibrate for measuring altitude above ground level (AGL)
    alt1.setPressureOffset(currentPressure)
    currentBar = currentPressure * _PASCAL_CONVERSION_FACTOR
    print("%s setting altimeter to: %.2f" % \
          (getTimeStamp(), currentBar)) 


    # Create an rrdtool database if it does not exist.
    if not os.path.exists(_RRD_FILE):
        print("database does not exist\n"\
              "Run createAltimeterRrd.py to create new database.")

    # Define rrdtool database handler instance.
    rrdb = rrdbase.rrdbase( _RRD_FILE, _CHARTS_DIRECTORY, _CHART_WIDTH, \
                            _CHART_HEIGHT, verboseMode, debugMode )
##end def

def loop():
    # Last time the data file to the web server updated
    lastCheckForUpdateTime = -1
    # Last time day charts were generated
    lastDayChartUpdateTime = -1
    # Last time the rrdtool database updated
    lastDatabaseUpdateTime = -1
 
    # Main loop
    while True:

        currentTime = time.time() # get current time in seconds

        # Every update period, get and process mpl3115a2 sensor data.
        if currentTime - lastCheckForUpdateTime > sensorPollingInterval:
            lastCheckForUpdateTime = currentTime
            
            # Check if user has clicked the Altitude Reset button.
            checkForAltimeterReset(alt1)

            # Get MPL3115 sensor data.
            dData = {}
            result = getSensorData(alt1, dData)

            # If the sensor is online and the data successfully parsed, 
            # then convert the data.
            if result:
                result = convertData(dData)

            # If the data successfully converted, then the write the data
            # to the output data file.
            if result:
                writeOutputDataFile(dData)

            # At the rrdtool database update interval write the data to
            # the rrdtool database.
            if result and (currentTime - lastDatabaseUpdateTime) > \
              _DATABASE_UPDATE_INTERVAL:   
                lastDatabaseUpdateTime = currentTime
                # Update the round robin database with the parsed data.
                result = rrdb.updateDatabase((dData['date'], 
                                              dData['altitude'],
                                              dData['bar'],
                                              dData['tempF']))
            ## end if
            setStatus(result) 

        # At the day chart generation interval generate day charts.
        if currentTime - lastDayChartUpdateTime > _CHART_UPDATE_INTERVAL:
            lastDayChartUpdateTime = currentTime
            p = multiprocessing.Process(target=generateDayGraphs, args=())
            p.start()

        # Relinquish processing back to the operating system until
        # the next update interval.  Also provide processing time
        # information for debugging and performance analysis.
        elapsedTime = time.time() - currentTime
        if verboseMode:
            if result:
                print("update successful: %6f sec\n"
                      % elapsedTime)
            else:
                print("update failed: %6f sec\n"
                      % elapsedTime)
        remainingTime = sensorPollingInterval - elapsedTime
        if remainingTime > 0.0:
            time.sleep(remainingTime)
    ## end while
## end def

if __name__ == '__main__':
    setup()
    loop()

##end module
