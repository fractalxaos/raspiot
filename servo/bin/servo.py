#!/usr/bin/python3 -u

# This interactive python program moves a servo using the GPIO
# pulse width modulation functions. The user may enter the
# following:
#    n an integer angle between 0 and 180 degrees
#   'c' for continuous oscillation mode
#   's' to exit the program

   ### IMPORT MODULES ###

import RPi.GPIO as GPIO
import os
import sys
import math
import psutil
import signal
import time


   ### PARAMETER DEFAULTS ###

_DEFAULT_ANGLE = 0.0

   ### SERVO CONFIGURATION ###

SERVO_CONTROL_PIN = 19 # GPIO pin number
PWM_FREQUENCY = 50 # Hertz
SERVO_MIN_PULSE_WIDTH = 0.75 # milliseconds
SERVO_MAX_PULSE_WIDTH = 2.25 # milliseconds
PWM_PERIOD = 1000.0 / PWM_FREQUENCY  # pulse period in milliseconds
MS_PER_DEGREE = (SERVO_MAX_PULSE_WIDTH - \
                 SERVO_MIN_PULSE_WIDTH) / 180.0 # milliseconds

   ### GLOBAL VARIABLES ###

angle = _DEFAULT_ANGLE
runContinuous = False
pwm = None

# House keeping items.
killAllInstances = False
verboseMode = False

def setDutyCycle(angle):
    """
    Description:
    Sets the duty cycle of the PWM signal to the servo.
    Parameters:
        angle - the angle to which to move the servo arm
    Returns: nothing.
    """
    # Duty cycle (in percent) is 100 times pulse width divided by the
    # period tpwm of the pulse width modulated signal.  The period is
    # the reciprocal of the frequency of the pulse width modulated signal.
    #    ____                                  ____
    #   |    |________________________________|    |_________
    #   |<-->|
    #    tmin 
    #   |<---------------tpwm---------------->|
    #
    #    _________                             _________
    #   |         |___________________________|         |____
    #   |<--tmax->|
    #   |<---------------tpwm---------------->|
    #
    # The servo is controlled by a pulse width modulated signal where
    # the width of the pulse varies from a minimum value tmin to a
    # maximum value tmax.  These values defined by the global constants
    # SERVO_MIN_PULSE_WIDTH and SERVO_MAX_PULSE_WIDTH.  The pulse width,
    # tp, where tmin < tp < tmax, determines the number of degrees the
    # servo arm moves.  For a servo arm capable of 180 degrees movement,
    #
    #    tp = ((tmax - tmin)/180)*angle + tmin
    #
    # where angle is in degrees, and 
    #     
    #    duty cycle(%) = 100*tp/tpwm
    #
    # where tpwm is the period of the pulse width modulated signal.

    pulsewidth = MS_PER_DEGREE * angle + SERVO_MIN_PULSE_WIDTH
    dutyCycle = 100.0 * pulsewidth / PWM_PERIOD # percent duty cycle
    pwm.ChangeDutyCycle(dutyCycle)
#end def

def setServo(angle):
    """
    Description:
    Moves the servo arm to a specific angle and leaves it there.
    """
    # Move the servo to the supplied angle.
    setDutyCycle(angle)
    time.sleep(1.0)
## end def

def continuousMotion():
    """
    Description:
    Moves the servo arm back and forth in continuous motion.
    """
    # Set initial servo angle to 0.
    setServo(0)
    # Oscillate the servo arm back and forth between 0 and 180 degress.
    while True:
        # In small increments, move the servo arm forward 180 degrees.
        for i in range(0, 180, 1):
            setDutyCycle(i)
            time.sleep(0.01) # controls the speed of forward movement
        # In small increments, move the servo arm backward 180 degrees.
        for i in range(180, 0, -1):
            setDutyCycle(i)
            time.sleep(0.01) # controls the speed of backward movement
    ## end while
## end def

def setup():
    """
    Description:
    Sets up the GPIO interface mode, and sets up to output a pulse
    width modulated signal the GPIO output pin connected to the servo
    control input (white lead). 
    """
    global pwm
    # Setup the GPIO interface.
    GPIO.setmode(GPIO.BCM) # sets Broadcom pin numbering scheme
    GPIO.setwarnings(False)
    # Setup the pin connected to the servo control lead to output a pulse
    # width modulated signal.
    GPIO.setup(SERVO_CONTROL_PIN, GPIO.OUT)
    pwm = GPIO.PWM(SERVO_CONTROL_PIN, PWM_FREQUENCY)
    pwm.start(0)
## end def

def cleanup(signal, frame):
    """
    Description:
    Resets the servo arm back to zero degrees and restores the
    GPIO interface to default conditions.
    """
    pwm.ChangeDutyCycle(0) # set servo angle to 0 degrees
    GPIO.output(SERVO_CONTROL_PIN, False)
    GPIO.cleanup() # reset GPIO to defaults
    exit(0)
## end def

def killOtherInstances():
    """
    Description:
    Allows only one instance to run at a time to avoid
    possible smbus bus contention.
    """
    thisProc = os.path.basename(__file__)

    # Get the list of currently running processes that have the same
    # name as this process, for example, have the name "servo.py".
    lProcs = []
    for proc in psutil.process_iter():
        if proc.name() == thisProc:
            lProcs.append(proc)
    # Remove from the list the most recent instance (this instance)
    # of this process.
    lProcs = lProcs[:-1]
    # Kill all previously instantiated instances.
    for proc in lProcs:
        os.kill(proc.pid, signal.SIGTERM)
## end def

def getCLarguments():
    """
    Description:
    Gets command line arguments and verifies parameters.  Valid
    arguments are
        -k kill all instances
        -a {number} angle (degrees)
        -c continuous motion
        -v verbose debug mode
    Parameters: None
    Returns: nothing.
    """
    global angle, runContinuous, killAllInstances, verboseMode

    index = 1
    try:
        while index < len(sys.argv):
            if sys.argv[index] == '-a':
                angle = float(sys.argv[index + 1])
                assert angle >= 0 and angle <= 180, \
                    'invalid angle'
                index += 1
            elif sys.argv[index] == '-c':
                runContinuous = True
            elif sys.argv[index] == '-k':
                killAllInstances = True
            elif sys.argv[index] == '-v':
                verboseMode = True
            else:
                cmd_name = sys.argv[0].split('/')
                print('Usage: %s [-a angle] [-c continuous mode] ' \
                      '[-k kill all instances] [-v verbose mode]' \
                      % cmd_name[-1])
                exit(-1)
            index += 1
        ## end while
    except Exception as exError:
        errorMsg = str(exError)
        print(errorMsg)
        exit(-1)
    ## end try
    return
## end def

def main():
    # Clean up GPIO when this process killed.
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    getCLarguments()

    killOtherInstances()
    if killAllInstances:
        exit(0)
    time.sleep(0.01) # delay to allow GPIO cleanup of previous instances

    setup()
    
    if runContinuous:
        # Move servo in continuous motion, back and forth through its
        # complete range of motion.
        continuousMotion()
    else:
        setServo(angle)

    cleanup(0,0)
## end def

if __name__ == '__main__':
    main()
## end module
