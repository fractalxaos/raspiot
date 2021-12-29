#!/usr/bin/python3 -u
#
# Module: ads1115.py
#
# Description: This module acts as an interface between the ADS1115
# analog to digital converter and downstream applications that use the
# data.  This module acts as a library module that
# can be imported into and called from other Python programs.
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
#
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

import smbus
import time

# Define default sm bus address.
_DEFAULT_BUS_ADDRESS = 0x48
_DEFAULT_BUS_NUMBER = 1

# Define device registers.
_CONVERSION_REG = 0x00
_CONFIG_REG = 0x01
_LO_THRESH_REG = 0X02
_HI_THRESH_REG = 0X03

# Define timeout waiting for sensor output ready.
_SENSOR_READ_TIMEOUT = 2.0

# Define the default sensor configuration.  See the ADS1115 data sheet
# for meaning of each bit.  The following bytes are written to the
# configuration register
#
# byte 1 | OS  |       MUX       |       PGA       | MODE|
#        | d15 | d14 | d13 | d12 | d11 | d10 |  d9 |  d8 |
#        |  1  |  1  |  0  |  0  |  0  |  0  |  1  |  0  |
#
# byte 2 |        DR       | C_M | C_P | C_L | COMP_QUE  |
#        |  d7 |  d6 |  d5 |  d4 |  d3 |  d2 |  d1 |  d0 | 
#        |  1  |  0  |  0  |  0  |  0  |  0  |  1  |  1  |
#
_DEFAULT_CONFIG = 0xC283

# Module scope global instance for testing purposes
adc1 = None

class ads1115:

    def __init__(self, sAddr=_DEFAULT_BUS_ADDRESS,
                       sbus=_DEFAULT_BUS_NUMBER,
                       config=_DEFAULT_CONFIG,
                       debug=False):
        """
        Initialize the MPL3115 sensor at the supplied address (default
        address is 0x60), and supplied bus (default is 1).  Creates
        a new SMBus object for each instance of this class.  Writes
        configuration data (two bytes) to the MPL3115 configuration
        registers.
        """

        # Instantiate a smbus object.
        self.sensorAddr = sAddr
        self.bus = smbus.SMBus(sbus)
        self.config = config # control register 1 configuration
        self.debugMode = debug

        # Calculate scaling factor for computing input voltage from
        # conversion register value.  The scaling factor determined
        # by the setting of the programable gain amplifier (PGA).
        # For meaning of PGA settings see datasheet pages 17 and 28.
 
        # Get PGA[2:0] from bits 11:9 of configuration data.
        PGA_val =  (config & 0x0E00) >> 9

        # Calculate volts represented by lsb of conversion register.        
        if PGA_val == 0:
            self.volts_lsb = 187.5E-6
        elif PGA_val >= 5:
            self.volts_lsb = 7.8125E-6
        else:
            self.volts_lsb = 2.0**float(5 - PGA_val) * 7.8125E-6

        # Write configuration data to configuration register _CONFIG_REG.
        # Break up configuration data into bytes.
        lData = [config >> 8]
        lData += [config & 0xFF]
 
        if self.debugMode:
            print('PGA_val: %d' % PGA_val)
            printBytes(lData, 'config reg')
         
        # Send the bytes to the ADS1115 configuration register.
        self.bus.write_i2c_block_data(self.sensorAddr, _CONFIG_REG, lData)
        time.sleep(0.1)
    ## end def

    def setInputSource(self, source):
        """
        Description:
        Sets the ADS1115 input multiplexer to one of eight possible
        configurations.  See the table on datasheet page 28, MUX section,
        for more information about these configurations.

        Parameters:
        source - integer between 0 and 7, inclusive. Common settings for
                 measuring input to common ground are
                     4 - AIN0
                     5 - AIN1
                     6 - AIN2
                     7 - AIN3
        Returns: Nothing
        """
        assert isinstance(source, int) and source >= 0 and source <= 7, \
            'invalid input source'

        lData = self.bus.read_i2c_block_data(self.sensorAddr, _CONFIG_REG, 2)
        config = lData[0] << 8 | (lData[1] & 0xFF)

        self.config = (config & 0x8FFF) | (source << 12) 

        # Break up configuration data into bytes.
        lData = [self.config >> 8]
        lData += [self.config & 0xFF]

        if self.debugMode:
            print('setting input source: %d' % source)
            printBytes(lData, 'config reg')

        self.bus.write_i2c_block_data(self.sensorAddr, _CONFIG_REG, lData)
        time.sleep(0.1)
    ## end def

    def getVoltage(self):
        """
        Description:
        Gets the voltage on the input of the ADS1115.  Calculates the
        voltage based on the configuration of the programable gain
        amplifier.
        """
        lData = self.bus.read_i2c_block_data(self.sensorAddr,
                _CONVERSION_REG, 2)

        if self.debugMode:
            printBytes(lData, 'conversion register')
                  
        val = lData[0] << 8 | (lData[1] & 0xFF)
        
        if val > 0x7FFF:
            val -= 0xFFFF
        return val * self.volts_lsb
    ## end def
## end class

    ### HELPER FUNCTIONS ###

def printBytes(lData, sLabel):
    nBytes = len(lData)
    tBytes = ()
    for i in range(nBytes):
        tBytes += (format(lData[i], '08b')),
    sFmt = '%s:' % sLabel
    sFmt += nBytes * ' %s'
    print(sFmt % tBytes)
## end def

    ### TEST FUNCTIONS ###

def test():
    global adc1

    adc1 = ads1115(config=0xC283, debug=True)
    adc1.setInputSource(4)

    volts = adc1.getVoltage()
    print('volts: %.4f' % volts)
    del adc1
    adc1 = ads1115(config=0xC483, debug=True)
    volts = adc1.getVoltage()
    print('volts: %.4f' % volts)
## end def

if __name__ == '__main__':
    try:    
        test()
    except KeyboardInterrupt:
        print()  # clean up on CTRL+C exit




