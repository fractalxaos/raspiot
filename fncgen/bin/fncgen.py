#!/usr/bin/python3 -u
"""
Script: fncgen.py

Description:
This script generates waveforms to be output via the MCP4725 digital
to analog converter I2C device.

Note: the following line must be added to the /etc/sudoers
file so that the www-data user can start this as a process.
 
   www-data ALL=(ALL) NOPASSWD: /home/pi/bin/fncgen.py

Copyright 2021 Jeff Owrey
   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.
   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see http://www.gnu.org/license.

Revision History
  * v10 released 12 Dec 2021 by J L Owrey; first release

12345678901234567890123456789012345678901234567890123456789012345678901234567890
"""
import os
import sys
import math
import psutil
import signal
import time

   ### PARAMETER DEFAULTS ###

_DEFAULT_WAVEFORM = 'sin' # waveform function
_DEFAULT_FREQUENCY = 20.0 # Hertz
_DEFAULT_AMPLITUDE = 1.6  # Volts
_DEFAULT_DUTYCYCLE = 0.5  # percent

   ### ADC CONFIGURATION ###

_SAMPLE_RATE = 1000 # samples per second
_DAC_RESOLUTION = 4095
_MAX_AMPLITUDE = 3.2 # volts
_MAX_FREQUENCY = 100.0 # hertz
_AVAILABLE_WAVEFORMS = ['dc', 'sin', 'sqr', 'tri', 'saw']

   ### GLOBAL VARIABLES ###

waveform = _DEFAULT_WAVEFORM
frequency = _DEFAULT_FREQUENCY
amplitude = _DEFAULT_AMPLITUDE
dutyCycle = _DEFAULT_DUTYCYCLE
dac1 = None

# House keeping items.
debugMode = False
verboseMode = False
killAllInstances = False

   ### WAVEFORM FUNCTIONS ###

def getDcWave(amplitude=_DEFAULT_AMPLITUDE):
    """
    Description: Generates a DC, that is, constant waveform.
    Parameters:
        amplitude - output level of the DC waveform
    Returns: a list object containing a single element, the amplitude
        of the DC waveform
    """
    dacVal = (amplitude / _MAX_AMPLITUDE) * _DAC_RESOLUTION
    wfrm = [round(dacVal)]
    return wfrm
## end def
    
def getSineWave(frequency=_DEFAULT_FREQUENCY,
                amplitude=_DEFAULT_AMPLITUDE):
    """
    Description: Generates a sine wave.
    Parameters:
        frequency - the frequency in Hertz
        amplitude - the signal level in Volts
    Returns: a list object containing the waveform data
    """
    numSamples = getSampleRate(frequency)
    amplitude = (amplitude / _MAX_AMPLITUDE) * _DAC_RESOLUTION / 2.0
    dRadns = 2.0 * math.pi / numSamples
    phase = math.pi / 2.0 # set phase to begin at zero amplitude
    wfrm = []
    for i in range(numSamples):
        dacVal = amplitude * (math.sin(i * dRadns - phase) + 1.0)  
        wfrm.append(round(dacVal))
    return wfrm
## end def

def getSquareWave(frequency=_DEFAULT_FREQUENCY,
                amplitude=_DEFAULT_AMPLITUDE,
                dutyCycle=0.5):
    """
    Description: Generates a square wave.
    Parameters:
        frequency - the frequency in Hertz of the square wave
        amplitude - the signal level in Volts
        dutyCycle - the duty cycle in percent of the square wave
    Returns: a list object containing the waveform data
    """
    numSamples = getSampleRate(frequency)
    amplitude = (amplitude / _MAX_AMPLITUDE) * _DAC_RESOLUTION
    numSamplesHigh = int(dutyCycle * numSamples)
    numSamplesLow = int((1.0 - dutyCycle) * numSamples)
    wfrm = []
    for i in range(numSamplesHigh):
        dacVal = amplitude
        wfrm.append(round(dacVal))
    for i in range(numSamplesLow):
        dacVal = 0
        wfrm.append(round(dacVal))
    return wfrm
## end def

def getTriangleWave(frequency=_DEFAULT_FREQUENCY,
                amplitude=_DEFAULT_AMPLITUDE):
    """
    Description: Generates a triangle wave.
    Parameters:
        frequency - the frequency in Hertz
        amplitude - the signal level in Volts
    Returns: a list object containing the waveform data
    """
    numSamples = getSampleRate(frequency)
    amplitude = (amplitude / _MAX_AMPLITUDE) * _DAC_RESOLUTION
    numSamplesdiv2 = int(numSamples / 2.0)
    dAmp = amplitude / numSamplesdiv2
    wfrm = []
    for i in range(numSamplesdiv2):
        dacVal = dAmp * i
        wfrm.append(round(dacVal))
    for i in range(numSamplesdiv2):
        dacVal = amplitude - dAmp * i  
        wfrm.append(round(dacVal))
    return wfrm
## end def

def getSawtoothWave(frequency=_DEFAULT_FREQUENCY,
                amplitude=_DEFAULT_AMPLITUDE):
    """
    Description: Generates a sawtooth wave.
    Parameters:
        frequency - the frequency in Hertz
        amplitude - the signal level in Volts
    Returns: a list object containing the waveform data
    """
    numSamples = getSampleRate(frequency)
    amplitude = (amplitude / _MAX_AMPLITUDE) * _DAC_RESOLUTION
    dAmp = amplitude / numSamples
    wfrm = []
    for i in range(numSamples):
        dacVal = dAmp * i
        wfrm.append(round(dacVal))
    return wfrm
## end def

_WAVEFORM_FUNCTIONS = [getDcWave, getSineWave, getSquareWave, getTriangleWave, \
    getSawtoothWave]

    ### HELPER FUNCTIONS ###

def getSampleRate(frequency):
    """
    Description: Calculates the number of waveform samples to generate
    based on the frequency of the waveform.  Due to hardware limitations
    the number of samples must be reduced as frequency goes higher,
    as the hardware cannot handle more than about 1000 samples
    per second.
    Parameters:
        frequency - the frequency of the waveform
    Returns: the number of waveform samples to calculate
    """
    # Calculate samples per hertz.  That is, samples per one period
    # of the waveform, based on speed of DAC.
    numSamples = round((1.0 / frequency) * _SAMPLE_RATE)
    return numSamples
## end def

def outputWaveform(waveformData, frequency):
    """
    Description: Outputs waveform data to the DAC via the mcp4725
    driver module.
    Parameters:
        waveformData - a list object containing the waveform data
        frequency - the frequency of the waveform
    Returns: nothing
    """
    # Zero Hertz wave is DC.  Set the DAC
    # and leave it there.
    if waveform == 'dc':
        dac1.write_fast(waveformData[0])
        if verboseMode:
            print("DC level: %s volts" % amplitude)
        while True:
            time.sleep(0.5)

    # The sample period (tSample) must be determined emperically by
    # measuring the time (tWrite) reguired to write a sample to the
    # DAC. To get the sample period add a small guard time before sending
    # the next sample to the DAC.
    #
    # |<----tSample----->|
    # |                  |
    # |<-tWrite-->|      |
    # |___________|______|___________ ______ ___
    # X___________X______X___________X______X___
    #       |        |        |
    #       |        |        + next sample written to DAC
    #       |        |
    #       |        +--- guard time between samples
    #       |
    #       +--- sample written to DAC
    #
    numSamples = len(waveformData)
    tSample = 1.0/_SAMPLE_RATE

    if verboseMode:
        print('numSamples: %d tSample: %.10f' % \
              (numSamples, tSample))

    # Set the index of the last element in the waveform array, which is
    # always one less than the array length.
    maxPtr = numSamples - 1
    # Set the waveform array pointer to the first element in the array.
    ptr = 0 
    # Initialize the previous DAC write time.
    previousWriteTime = time.time()
    # Initialize elapsed time counter initial value.
    init_time = time.time()
    while True:
        currentTime = time.time()
        # Samples are sent to the DAC at sampleRate equal to hardcoded
        # _SAMPLE_RATE constant.
        if (currentTime - previousWriteTime) >= tSample:
            previousWriteTime = currentTime
            
            if ptr > maxPtr:
                # The complete waveform for one cycle has been sent to
                # the DAC, so set  the waveform sample pointer back
                # the beginning of the waveform array.
                ptr = 0
                if verboseMode:
                    t_period = time.time() - init_time
                    t_sample = t_period / numSamples
                    print('period: %.6f  rate: %.8f' % (t_period, t_sample))
                    init_time = currentTime
            ## end if

            dac1.write_fast(waveformData[ptr])
            ptr += 1

            elapsedTime = time.time() - currentTime
            remainingTime = tSample - elapsedTime - .001
            if remainingTime > 0.0:
                time.sleep(remainingTime)
        ## end if
    ## end while
## end def

def writeOutputDataFile(fname, sData):
    """
    Description: This function used for test purposes to verify
    the the waveform data send to the mcp4725 DAC.
    Parameters:
        fname - the name of the output file
        sData - the data string to write to the output file
    Returns: True if successful, False otherwise
    """
    try:
        fc = open(fname, "w")
        fc.write(sData)
        fc.close()
    except Exception as exError:
        print("write output file failed: %s" % \
              (exError))
        return False

    return True
##end def

def killOtherInstances():
    """
    Description: Allows only one instance to run at a time to avoid
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

def terminateProcess(signal, frame):
    """
    Description: Sets DAC to zero output voltage when this program gets
    terminated. Setting the DAC to zero protects the DAC from potential
    shorts.
    Parameters:
        signal - dummy parameter
        frame  - dummy parameter
    Returns: nothing
    """
    # To prevent shorts always set the DAC back to zero volts before
    # exiting this process.
    dac1.write_fast(0)
    if verboseMode:
        print()
    exit(0)
# end def

def getCLarguments():
    """
    Description: Get command line arguments.
    Parameters: none
    Returns: nothing

    Usage: fncgen -w WAVEFORM -f FREQUENCY

    -w
      dc  - DC constant signal level
      sin - sine wave (default)
      sqr - square wave
      tri - triangle wave
      saw - sawtooth wave

    -f frequency in Hz (default 100 Hz)

    -a amplitude in volts (default 1.0 volts)

    -d duty cycle of square wave (default 0.5)

    -k kill all running instances and exit

    -v verbose debug mode
    """
    global waveform, frequency, amplitude, dutyCycle
    global killAllInstances, verboseMode

    index = 1
    try:
        while index < len(sys.argv):
            if sys.argv[index] == '-w':
                waveform = str(sys.argv[index + 1]).lower()
                assert waveform in _AVAILABLE_WAVEFORMS, \
                    'invalid waveform'
                index += 1
            elif sys.argv[index] == '-f':
                frequency = float(sys.argv[index + 1])
                assert frequency >= 0.0 and frequency <= _MAX_FREQUENCY, \
                    'invalid frequency'
                index += 1
            elif sys.argv[index] == '-a':
                amplitude = float(sys.argv[index + 1])
                assert amplitude >= 0.0 and amplitude <= _MAX_AMPLITUDE, \
                    'invalid amplitude'
                index += 1
            elif sys.argv[index] == '-d':
                dutyCycle = float(sys.argv[index + 1])
                assert dutyCycle >= 0.0 and dutyCycle <= 1.0, \
                    'invalid dutyCycle'
                index += 1
            elif sys.argv[index] == '-k':
                killAllInstances = True
            elif sys.argv[index] == '-v':
                verboseMode = True
            else:
                cmd_name = sys.argv[0].split('/')
                print('Usage: %s [-w waveform] [-f freq] [-a amp] ' \
                      '[-d duty] [-v verbose mode]' % cmd_name[-1])
                exit(0)
            index += 1
    except Exception as exError:
        errorMsg = str(exError)
        if errorMsg.find('invalid') >= 0: 
            print(errorMsg)
        exit(-1)

    return
## end def

    ### MAIN ROUTINE ###

def main():
    """
    Description: Main routine.
    Parameters: none
    Returns: nothing
    """
    global dac1

    # Register callback function to do cleanup when this script terminated
    # by CTL-C or kill signal.
    signal.signal(signal.SIGTERM, terminateProcess)
    signal.signal(signal.SIGINT, terminateProcess)

    # Get command line arguments.
    getCLarguments()

    # Generate waveform data for selected waveform
    if frequency <= 0 or waveform == 'dc':
        waveformData =  getDcWave(amplitude)
    elif waveform == 'sin':
        waveformData = getSineWave(frequency, amplitude)
    elif waveform == 'sqr':
        waveformData = getSquareWave(frequency, amplitude, dutyCycle)
    elif waveform == 'tri': 
        waveformData = getTriangleWave(frequency, amplitude)
    elif waveform == 'saw':  
        waveformData = getSawtoothWave(frequency, amplitude)

    # Write new line delimited waveform data to file for debug purposes.
    if debugMode:
        sWaveformData = '\n'.join(map(str,waveformData))
        print('samples per Hz: %d' % len(waveformData))
        writeOutputDataFile('waveformData.csv', sWaveformData)
        exit(0)

    # Kill all other running instances of this program.  Killing
    # other instances prevents possible smbus contention.
    killOtherInstances()

    # Create an instance of the digital to analog converter driver class.
    import mcp4725
    dac1 = mcp4725.mcp4725(debug=False)

    # Kill this instance and make a clean exit if -k option entered on
    # the command line.  Otherwise output the selected waveform. 
    if killAllInstances:
        terminateProcess(0,0)
    else:
        outputWaveform(waveformData, frequency)
## end def

if __name__ == '__main__':
    main()

## end module
