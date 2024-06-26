#!/usr/bin/python3 -u
#
# Module: mpl3115.py
#
# Description: This module acts as an interface between the MPL3115A2
# sensor and downstream applications that use the data.  Class methods get
# pressure, altitude, and temperature data from the MPL3115 sensor.  This
# module acts as a library module that can be imported into and called
# from other Python programs.
#
# Notes:
# 1. Five bytes must be read from the output registers: three bytes from
#    OUT_P register and two bytes from OUT_T register.  Five bytes at a time
#    must be read in order to flush these registers for the next data
#    data acquisition.  Otherwise random data may be in the output
#    register.
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
#   * v10 released 01 June 2021 by J L Owrey; first release
#   * v1.1 issued 23 May 2024 by J L Owrey; make printBytes into a class
#     method, improve setting control register, correct errors in comments
#
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

import smbus
import time

# Define default sm bus address.
_DEFAULT_BUS_ADDRESS = 0x60
_DEFAULT_BUS_NUMBER = 1

# Define device register addresses.
_STATUS_REG = 0x00
_OUT_P_MSB_REG = 0x01
_ID_REG = 0x0C
_PT_DATA_CFG_REG = 0x13
_BAR_IN_MSB_REG = 0x14
_CONTROL_REG = 0x26

# Define timeout waiting for sensor output ready.
_SENSOR_READ_TIMEOUT = 2.0

# Define the default sensor configuration.  See the MPL3115 data sheet
# for meaning of each bit.  The following bytes are written to the
# configuration register
#               10111001 0xB8
#   |      10        |  111   |      000     |
#   | altimeter mode | OSR128 | standby mode |
_DEFAULT_CONFIG = 0xB8

class  mpl3115:

    def __init__(self, sAddr=_DEFAULT_BUS_ADDRESS,
                       sbus=_DEFAULT_BUS_NUMBER,
                       config=_DEFAULT_CONFIG,
                       debug=False):
        """
        Description: Initialize the MPL3115 sensor at the supplied
        address (default address is 0x60), and supplied bus (default
        is 1).  Creates a new SMBus object for each instance of this
        class.  Writes configuration data (two bytes) to the MPL3115 
        configuration registers.

        Parameters:
            sAddr - the serial bus address of the MPL3115 device
            sbus  - the bus number of the bus to which the MPL3115 connected
            config - one byte MPL3115 configuration
            debug - boolean value: True for debug mode, False otherwise
        Returns: nothing
        """

        # Instantiate a smbus object.
        self.sensorAddr = sAddr
        self.bus = smbus.SMBus(sbus)
        self.config = config # control register 1 configuration
        self.debugMode = debug

        # Write configuration data to control register _CONTROL_REG. Set
        # MPL3115 to standby mode.
        #               10111000 0xB8
        #   |      10        |  111   |      000     |
        #   | altimeter mode | OSR128 | standby mode |
        config_reg = self.config & 0b11111110
        self.bus.write_byte_data(self.sensorAddr, _CONTROL_REG, config_reg)

        # Write data to data configuration register PT_DATA_CFG_REG.
        #		          00000111 0x07
        #   | 00000 |  1   |   1   |   1   |
        #   |   X   | DREM | PDEFE | TDEFE |
        #
        #   X - don't care
        #   DREM - Data ready event mode for all events
        #   PDEFE - Pressure/Altitude data ready event flag
        #   TDEFE - Temperature data ready event flag
        self.bus.write_byte_data(self.sensorAddr, _PT_DATA_CFG_REG, 0x07)

        if self.debugMode:
            data = self.getInfo()
            print("manufacturer ID: %s \nstatus register: %s\n"\
                  "control register: %s\n" % data)
    ## end def

    def getInfo(self):
        """
        Description: Gets status and configuration data from MPL3115.

        Parameters: none
        Returns: three bytes of data
        """
        # Read manufacture identification data.
        mfcid = self.bus.read_byte_data(self.sensorAddr, _ID_REG)
        mfcidB1 = format(mfcid, "08b")
        # Read status data.
        status = self.bus.read_byte_data(self.sensorAddr, _STATUS_REG)
        statusB1 = format(status, "08b")
        # Read configuration data.
        control = self.bus.read_byte_data(self.sensorAddr, _CONTROL_REG)
        controlB1 = format(control, "08b")
        return (mfcidB1, statusB1, controlB1)
    ## end def

    def pollForData(self):
        """
        Description: Waits for MPL3115 to signal that new data is ready
        or until times out.

        Parameters: none
        Returns: nothing
        """
        # Start a timer for smbus timeout.
        init_time = time.time() 
        # Poll sensor status for new data. It the timer times out, raise
        # a smbus time out exception.
        while time.time() - init_time < _SENSOR_READ_TIMEOUT:
            data = self.bus.read_byte_data(self.sensorAddr, _STATUS_REG)
            dataReady = data & 0b00001000 # bit 4 high indicates data ready
            if dataReady != 0:
                if self.debugMode:
                    print('sensor read time: %f sec' % \
                         (time.time() - init_time))
                time.sleep(0.05)
                return
            time.sleep(0.1)
        raise Exception('smbus timeout')
        return
    ## end def   

    def getAltitude(self):
        """
        Description: Gets altitude from the MPL3115.

        Parameters: none
        Returns: altitude in meters
        """
        # Set configuration register MPL3115 to active mode.
        #               10111001 0xB9
        #   |      10        |  111   |      001    |
        #   | altimeter mode | OSR128 | active mode |
        config_reg = self.config | 0b10000001
        # Write configuration data to control register _CONTROL_REG.
        self.bus.write_byte_data(self.sensorAddr, _CONTROL_REG, config_reg)

        # Poll data ready flag. Blocks further execution until
        # data ready or timeout.
        self.pollForData()
        
        # Read data back from OUT_DATA_REG, 5 bytes returned:
        # altitude MSB, altitude CSB, altitude LSB, temperature
        # MSB and temperature LSB.
        #        -------------------------------------------------
        #    bit |  7  |  6  |  5  |  4  |  3  |  2  |  1  |  0  |
        #        -------------------------------------------------
        # byte 1 | d19 | d18 | d17 | d16 | d15 | d14 | d13 | d12 |
        #        -------------------------------------------------
        # byte 2 | d11 | d10 | d9  | d8  | d7  |  d6 | d5  | d4  |
        #        -------------------------------------------------
        # byte 3 | d3  | d2  | d1  | d0  |  0  |  0  |  0  |  0  |
        #        -------------------------------------------------
        # The value is returned in Q16.4 format. The integer part
        # returned in d19-d4, a two's complement, 16 bit number.
        # The fractional part in d3-d0.        
 
        data = self.bus.read_i2c_block_data(self.sensorAddr, _OUT_P_MSB_REG, 5)

        if self.debugMode:
            self.printBytes(data, 'altitude register')
    
        # Convert the data to 20 bit signed number Q16.4
        binary_val = ((data[0] << 16 | data[1] << 8 | data[2]) >> 4)
        if binary_val > 0x7FFFF:
            binary_val -= 0xFFFFF

        # Convert binary altitude to decimal.  LSB equals 0.0625 meters.
        altitude = binary_val *  0.0625
        return altitude
    ## end def

    def getPressure(self, mode='P'):
        """
        Description: Gets pressure from the MPL3115.

        Parameters:
            mode - P for Pascals, B for inches of Mercury
        Returns: pressure in Pascals or inches of Mercury
        """
        # Set MPL3115 to active mode.
        #               00111001 0x39
        #   |      00        |  111   |      001    |
        #   | barometer mode | OSR128 | active mode |
        config_reg = (self.config & 0b00111110) | 0b00000001
        # Write configuration data to control register _CONTROL_REG.
        self.bus.write_byte_data(self.sensorAddr, _CONTROL_REG, config_reg)

        # Poll data ready flag. Blocks further execution until
        # data ready or timeout.
        self.pollForData()
        
        # Read data back from OUT_DATA_REG, 5 bytes returned:
        # pressure MSB, pressure CSB, pressure LSB, temperature
        # MSB and temperature LSB.
        #        -------------------------------------------------
        #    bit |  7  |  6  |  5  |  4  |  3  |  2  |  1  |  0  |
        #        -------------------------------------------------
        # byte 1 | d19 | d18 | d17 | d16 | d15 | d14 | d13 | d12 |
        #        -------------------------------------------------
        # byte 2 | d11 | d10 | d9  | d8  | d7  |  d6 | d5  | d4  |
        #        -------------------------------------------------
        # byte 3 | d3  | d2  | d1  | d0  |  0  |  0  |  0  |  0  |
        #        -------------------------------------------------
        # The value is returned in unsigned Q18.2 format. The
        # integer part returned in d19-d2 an unsignbed 18 bit number.
        # The fractional part in d1-d0.        
        data = self.bus.read_i2c_block_data(self.sensorAddr, _OUT_P_MSB_REG, 5)

        if self.debugMode:
            self.printBytes(data, 'pressure register')

        # Convert the data to 20-bits unsigned number Q18.2 format.
        binary_val = ((data[0] << 16 | data[1] << 8 | data[2]) >> 4)

        # Convert binary pressure to decimal.  LSB equals 0.25 Pascals.
        pressure = binary_val * 0.25

        if mode == 'B':
            return pressure / 3386.389 # convert to inches Hg
        elif mode == 'P':
            return pressure / 1000.0 # convert to kilo pascals
        else:
            print("invalid pressure mode option")
    ## end def

    def getTemperature(self, mode='C'):
        """
        Description: Gets temperature from the MPL3115.

        Parameters:
            mode - F for Fahrenheit, C for Celcius
        Returns: temperature in degrees Fahrenheit or Celcius
        """

        # Set MPL3115 to active mode.
        #               10111001 0xB9
        #   |      xx        |  111   |      001    |
        #   |  sensor mode   | OSR128 | active mode |
        config_reg = self.config | 0b00000001
        # Write configuration data to control register _CONTROL_REG.
        self.bus.write_byte_data(self.sensorAddr, _CONTROL_REG, config_reg)
        
        self.pollForData() # blocks execution until sensor data available

        # Read data back from OUT_DATA_REG, 5 bytes returned:
        # altitude MSB, altitude CSB, altitude LSB, temperature
        # MSB and temperature LSB.
        #        -------------------------------------------------
        #    bit |  7  |  6  |  5  |  4  |  3  |  2  |  1  |  0  |
        #        -------------------------------------------------
        # byte 4 | d11 | d10 | d9  | d8  | d7  |  d6 | d5  | d4  |
        #        -------------------------------------------------
        # byte 5 | d3  | d2  | d1  | d0  |  0  |  0  |  0  |  0  |
        #        -------------------------------------------------
        # The value is returned in Q8.4 format. The integer part
        # returned in d11-d4, a two's complement, 8 bit number.
        # The fractional part in d3-d0.        
        data = self.bus.read_i2c_block_data(self.sensorAddr, _OUT_P_MSB_REG, 5)

        
        if self.debugMode:
            self.printBytes(data, 'temperature register')

        # Convert the data to a 12 bit signed number Q12.4
        binary_val = ((data[3] << 8 | data[4]) >> 4)
        if binary_val > 0x7FF:
            binary_val -= 0xFFF 

        # Convert binary temperature to decimal.  LSB equals 0.0625 degress C.
        tempCelsius = binary_val * 0.0625

        if mode == 'F':
            # Convert Celsius to Fahrenheit.
            tempFahr = tempCelsius * 1.8 + 32.0
            return tempFahr
        elif mode == 'C':
            return tempCelsius
        else:
            print("invalid temperature mode option")
    ## end def

    def setPressureOffset(self, offset=101.325, mode='P'):
        """
        Description: Sets the pressure offset to zero the altimeter.

        Parameters:
            offset - the pressure offset in either Pascals or inches Mercury
            mode - B for inches Mercury, P for Pascals
        Returns: nothing
        """        
        if mode == 'B':
            # Convert inches mercury to Pascals.  The LSB of the
            # BAR_IN register equals 2.0 Pascals, so divide Pascals
            # by 2.
            pascalsDiv2 = int(round(offset * 3386.389 / 2.0))
        elif mode == 'P':
            # Convert kilo Pascals to Pascals.  The LSB of the
            # BAR_IN register equals 2.0 Pascals, so divide
            # Pascals by 2.
            pascalsDiv2 = int(round(offset * 1000.0 / 2.0))
        else:
            print("invalid pressure mode option")

        # Store the result of Pascals divided by 2 in two bytes
        # of the BAR_IN register.
        data = [ (pascalsDiv2 & 0xFF00) >> 8 ] # MSB
        data += [ pascalsDiv2 & 0xFF ] # LSB

        if self.debugMode:
            self.printBytes(data, 'pressure offset register')

        self.bus.write_i2c_block_data(self.sensorAddr,
                _BAR_IN_MSB_REG, data)
    ## end def

    def printBytes(self, lData, sLabel):
        """
        Description: Prints out data in binary format for debugging purposes.

        Parameters:
            lData - list of byte data to convert to binary
            sLabel - discriptive label of printed bytes
        Returns: nothing
        """    
        nBytes = len(lData)
        tBytes = ()
        for i in range(nBytes):
            tBytes += (format(lData[i], '08b')),
        sFmt = '%s:' % sLabel
        sFmt += nBytes * ' %s'
        print(sFmt % tBytes)
    ## end def
## end class

    ### TEST FUNCTIONS ###

def test():
    """
    Description: Verifies MPL3115 class methods.

    Parameters: none
    Returns: nothing
    """    
    # Initialize in debug mode the MPL3115 sensor.
    alt1 = mpl3115(0x60, 1, debug=True)
    # Calibrate for measureing altitude above ground level (AGL).
    alt1.setPressureOffset(alt1.getPressure())

    # Print out sensor values.
    while True:
        print("%6.2f m" % alt1.getAltitude())
 
        print("%6.2f kP" % alt1.getPressure())
        print("%6.2f inHg" % alt1.getPressure(mode='B'))

        print("%6.2f degC" % alt1.getTemperature())
        print("%6.2f degF\n" % alt1.getTemperature(mode='F'))
    ## end while
## end def

if __name__ == '__main__':
    try:    
        test()
    except KeyboardInterrupt:
        print()  # clean up on CTRL+C exit


