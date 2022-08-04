#!/usr/bin/python3 -u
#
# Module: mcp4725.py
#
# Description:
# This module acts as an hardware abstraction layer providing an
# interface between the MCP4725 device and higher level Python scripts.
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
 
import smbus
import time

# Define default sm bus address.
DEFAULT_BUS_ADDRESS = 0x61
DEFAULT_BUS_NUMBER = 1

# Define device registers.
_DAC_REG = 0x00

# Define write modes.
_WRITE_FAST_MODE = 0b00000000
_WRITE_DAC = 0b01000000
_WRITE_DAC_EEPROM = 0b01100000

# Set time out for eeprom write cycle to complete.
_EEPROM_POLL_WRITE_STATUS_TIMEOUT = 0.2

# Instance of this class for testing.
dac1 = None

class mcp4725:

    def __init__(self, sAddr=DEFAULT_BUS_ADDRESS,
                       sbus=DEFAULT_BUS_NUMBER,
                       debug=False):
        """
        Description: Creates an smbus object for use by this instance
        of this class.
        Parameters:
            sAddr - the serial bus address of the MCP4725 device
            sbus  - the bus number of the bus to which the MCP4725 connected
            debug - boolean value: True for debug mode, False otherwise
        Returns: nothing
        """
        # Instantiate a smbus object.
        self.sensorAddr = sAddr
        self.bus = smbus.SMBus(sbus)
        self.debugMode = debug
    ## end def

    def write_fast(self, val):
        """
        Description: Performs a 'fast mode' write to update the DAC value.
        Will not enter power down, update EEPROM, or any other state
        other than updating the DAC register.
        Parameters:
            val - 12 bit positive number to write to the DAC register
        Returns: nothing
        """
        assert 0 <= val <= 4095

        # Write data to the DAC register - 2 bytes in fast mode.
        #        -------------------------------------------------
        #    bit |  7  |  6  |  5  |  4  |  3  |  2  |  1  |  0  |
        #        -------------------------------------------------
        # byte 1 |  0  |  0  |  0  |  0  | d11 | d10 | d9  | d9  |
        #        -------------------------------------------------
        # byte 2 | d7  | d6  | d5  | d4  | d3  | d2  | d1  | d0  |
        #        -------------------------------------------------
        #
        # d11-d0 bits set the value to convert to analog.  The value
        # expressed as an unsigned integer between 0 and 4095.

        # Build bytes to send to device with updated value.
        bData = [_WRITE_FAST_MODE | (val >> 8)]
        bData.append(val & 0xFF)
        # The mcp4517 does not have a register offset pointer.  Therefore
        # the offset byte should be the first byte of the write command
        # string. The remain bytes are sent as the data block.
        self.bus.write_i2c_block_data(self.sensorAddr, bData[0], bData[1:])

        if self.debugMode:
            print('write fast: ', end='')
            for inx in range(0, len(bData)):
                bytDat = format(bData[inx], "08b")
                print('%s ' % bytDat, end='')
            print()
    ## end def

    def write_block(self, dataBlock):
        """
        Description: Writes a 32 byte block of data to the DAC at
        the maximum rate data can be written to the DAC register.
        Parameters:
            dataBlock - a list object containing the data to be
                        written to the DAC
        Returns: nothing
        """
        block = dataBlock.copy()
        bLen = len(block)
        bData = []
        while bLen > 0:
            # Parse each value in dataBlock into 2 bytes formatted
            # for the DAC fast write command.  
            val = block.pop(0)
            assert 0 <= val <= 4095
            bData.append(val >> 8)
            bData.append(val & 0xFF)
            bLen = len(block)
            # The write block data method can only send a maximum of
            # 32 bytes. Since each value in dataBlock is represented
            # 2 bytes, a maximum of 32 divided by 2, or 16 values can
            # be sent at a time.
            if bLen % 16 == 0:
                self.bus.write_i2c_block_data(self.sensorAddr, bData[0],
                    bData[1:])
                #print(bData)
                bData = []
    ## end def        

    def write_dac(self, val):
        """
        Description: Performs a write to update the DAC register.
        Will not enter power down, update EEPROM, or any other state other
        than updating the DAC register.
        Parameters:
            val - 12 bit positive value to write to the DAC register
        Returns: nothing
        """
        assert 0 <= val <= 4095

        # Write data to the DAC register - 3 bytes in normal mode.
        #        -------------------------------------------------
        #    bit |  7  |  6  |  5  |  4  |  3  |  2  |  1  |  0  |
        #        -------------------------------------------------
        # byte 1 |  0  |  1  |  0  |  X  |  X  |  0  |  0  |  X  |
        #        -------------------------------------------------
        # byte 2 | d11 | d10 | d9  | d8  | d7  | d6  | d5  | d4  |
        #        -------------------------------------------------
        # byte 3 | d3  | d2  | d1  | d0  |  X  |  X  |  X  |  X  |
        #        -------------------------------------------------
        # d11-d0 bits get the value to convert to analog.  The value
        # expressed as an unsigned integer between 0 and 4095.

        # Build bytes to send to device with updated value.
        bData = [_WRITE_DAC]
        bData.append(val >> 4)
        bData.append((val << 4) & 0xF0)
        self.bus.write_i2c_block_data(self.sensorAddr, bData[0], bData[1:])

        if self.debugMode:
            print('write dac: ', end='')
            for inx in range(0, len(bData)):
                bytDat = format(bData[inx], "08b")
                print('%s ' % bytDat, end='')
            print()
    ## end def

    def write_eeprom(self, val):
        """
        Description: Performs a write to update both the DAC register
        and the EEPROM.  Will not enter power down or any other state
        other than updating the EEPROM register.
        Parameters:
            val - 12 bit positive value to write to the DAC register
        Returns: nothing

        """
        assert 0 <= val <= 4095

        # Write data to the DAC register - 3 bytes in write mode.
        #        -------------------------------------------------
        #    bit |  7  |  6  |  5  |  4  |  3  |  2  |  1  |  0  |
        #        -------------------------------------------------
        # byte 1 |  0  |  1  |  1  |  X  |  X  |  0  |  0  |  X  |
        #        -------------------------------------------------
        # byte 2 | d11 | d10 | d9  | d8  | d7  | d6  | d5  | d4  |
        #        -------------------------------------------------
        # byte 3 | d3  | d2  | d1  | d0  |  X  |  X  |  X  |  X  |
        #        -------------------------------------------------
        # d11-d0 bits get the value to convert to analog.  The value
        # expressed as an unsigned integer between 0 and 4095.

        # Build bytes to send to device with updated value.
        val &= 0xFFF
        bData = [_WRITE_DAC_EEPROM]
        bData.append(val >> 4)
        bData.append((val << 4) & 0xF0)
        self.bus.write_i2c_block_data(self.sensorAddr, bData[0], bData[1:])
        self.poll_eeprom_write_status()

        if self.debugMode:
            print('write eeprom: ', end='')
            for inx in range(0, len(bData)):
                bytDat = format(bData[inx], "08b")
                print('%s ' % bytDat, end='')
            print()
    ## end def

    def read_dac(self):
        """
        Description: Reads the DAC register and extracts the
        DAC value.
        Parameters: none
        Returns: the 12 bit value in the register
        """
        # Read data from the DAC register - 3 bytes in write mode.
        #        -------------------------------------------------
        #    bit |  7  |  6  |  5  |  4  |  3  |  2  |  1  |  0  |
        #        -------------------------------------------------
        # byte 0 | RDY | POR |  X  |  X  |  X  | PD1 | PD2 |  X  |
        #        -------------------------------------------------
        # byte 1 | d11 | d10 | d9  | d8  | d7  | d6  | d5  | d4  |
        #        -------------------------------------------------
        # byte 2 | d3  | d2  | d1  | d0  |  X  |  X  |  X  |  X  |
        #        -------------------------------------------------
        # byte 3 |  X  | PD1 | PD2 |  X  | d11 | d10 | d9  | d8  |
        #        -------------------------------------------------
        # byte 4 | d7  | d6  | d5  | d4  | d3  | d2  | d1  | d0  |
        #        -------------------------------------------------
        # d11-d0 in bytes 1 and 2 contain the value in the DAC
        # register, while bytes 3 and 4 contain the value in the
        # EEPROM.  In both cases the value expressed as an unsigned
        # integer between 0 and 4095.

        # Read the DAC register and return the 12-bit DAC value.
        bData = self.bus.read_i2c_block_data(self.sensorAddr, _DAC_REG, 5)
 
        if self.debugMode:
            print('read dac: ', end='')
            for inx in range(0, len(bData)):
                bytDat = format(bData[inx], "08b")
                print('%s ' % bytDat, end='')
            print()

        # Grab the DAC value from last two bytes.
        # Reconstruct 12-bit value and return it.
        return (bData[1] << 4) | (bData[2] >> 4)
    ## end def

    def read_eeprom(self):
        """
        Description: Reads the DAC register and extracts the value in
        the EEPROM.
        Parameters: none
        Returns: the 12 bit EEPROM value in the register
        """
        # Read the DAC register and return the 12-bit EEPROM value.
        # Meaning of bits in the five bytes returned the same as described
        # above in the comments to the read_dac command.
        bData = self.bus.read_i2c_block_data(self.sensorAddr, _DAC_REG, 5)

        if self.debugMode:
            print('read dac: ', end='')
            for inx in range(0, len(bData)):
                bytDat = format(bData[inx], "08b")
                print('%s ' % bytDat, end='')
            print()

        # Grab the DAC value from last two bytes.
        eeprom_high = bData[3] & 0x0F
        eeprom_low = bData[4]
        # Reconstruct 12-bit value and return it.
        return ((bData[3] & 0x0F) << 8) | bData[4]
   ## end def

    def poll_eeprom_write_status(self):
        """
        Description: Periodically reads the DAC status byte and exits
        when the EEPROM write complete bit gets set.
        Parameters: none
        Returns: nothing
        """
        # Poll the EEPROM write complete status bit.  Raise an
        # exception if the polling process times out.

        time_start = time.time()
        while time.time() - time_start < _EEPROM_POLL_WRITE_STATUS_TIMEOUT:
            eeprom_write_status = self.bus.read_byte(self.sensorAddr)
            if self.debugMode and False:
                print("eeprom write status: %d" % eeprom_write_status)
            # The forth bit (b3) of the status registeer gets set
            # when the EEPROM write operation completes.
            if eeprom_write_status & 0x80 > 0:
                return;
            time.sleep(0.01)
        raise Exception("poll eeprom write status: timeout")
    ## end def

## end class

     ### TEST FUNCTIONS ###

def write_read_register():
    """
    Description: Verfies that values can be successfully written to
    the DAC register.
    Parameters: none
    Returns: nothing
    """
    dac1.write_fast(4011)
    dac_val = dac1.read_dac()
    print('dac read: %d\n' % dac_val)

    dac1.write_dac(2511)
    dac_val = dac1.read_dac()
    print('dac read: %d\n' % dac_val)

    dac1.write_eeprom(2933)
    eeprom_val = dac1.read_eeprom()
    print('eeprom val: %d\n' % eeprom_val)

    dac1.write_dac(0) 
    dac_val = dac1.read_dac()
    print('dac read: %d\n' % dac_val)

    dac1.write_eeprom(0)
    eeprom_val = dac1.read_eeprom()
    print('eeprom val: %d' % eeprom_val)
# end def

def write_fast():
    """
    Description: Verfies fast write mode at maximum sample rate.
    Parameters: none
    Returns: nothing
    """
    dac1.debugMode = False
    nSamples = 1000
    stepSize = int(4000 / nSamples)
    while True:
        time_init = time.time()
        for i in range(0, 4000, stepSize):
            dac1.write_fast(i)
        time_elapsed = time.time() - time_init
        tSample = time_elapsed / nSamples
        print('tSample: %f.6' % tSample)
## end def

def write_block():
    """
    Description: Verfies that blocks of data can be successfully
    written to the DAC register.
    Parameters: none
    Returns: nothing
    """
    dac1.debugMode = False
    nSamples = 1000
    dy = 4095.0 / float(nSamples)
    waveform = []
    for i in range(nSamples):
        waveform.append(round(i * dy))
    while True:
        time_init = time.time()
        dac1.write_block(waveform)
        period = time.time() - time_init
        tSample = period / nSamples
        print('period: %.10f  tSample: %.10f\n' % (period, tSample))
## end def

def set_voltage(volts):
    """
    Description: Verfies that the DAC can output a specific voltage.
    Parameters: none
    Returns: nothing
    """
    bVal = round((volts / 3.25) * 4096)
    dac1.write_fast(bVal)
## end def

if __name__ == '__main__':
    dac1=mcp4725(debug=True)

    try:
        #set_voltage(1.5)
        write_read_register()
        #write_fast()
        #write_block()
    except KeyboardInterrupt:
        dac1.write_fast(0)
        dac_val = dac1.read_dac()
        print('\ndac read: %d\n' % dac_val)
        exit(0)

## end module
