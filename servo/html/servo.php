<!DOCTYPE html>
<!-- Courtsey ruler
12345678901234567890123456789012345678901234567890123456789012345678901234567890
-->
<html>
<head>
<title>Servo Control</title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
.debugInfo {
    width: 100%;
    font: normal 16px arial, sans-serif;
    text-align: left;
    margin: auto;
}
</style>
</head>

<body>
<div class="debugInfo">

<?php

   ### CONSTANTS ###

define("DEBUG", false);

    ### GLOBAL VARIABLES ###

$runState = $_POST["runState"];
$angle = $_POST["angleSet"];

if (DEBUG) {
    echo "state: " . $runState . "<br>";
}

# Set servo state based on user input from web page.
if ($runState == "setAngle") {
    # Set servo angle based on user input from web page. 
    setAngle($angle);
} elseif ($runState == "startContinuous") {
    # Turn on continuous servo motion based on user input from web page. 
    continuousMotion(true);
} elseif ($runState == "stopContinuous") {
    # Turn off continuous servo motion based on user input 
    # from web page and restore previous angle setting. 
    continuousMotion(false);
    setAngle($angle);
}

function continuousMotion($continuous) {
    # Set servo run mode.
    if ($continuous) {
        # Start running servo in continuous mode.
        $cmd = "nohup sudo -u pi -S /home/pi/bin/servo.py -c";
    } else {
        # Stop running servo in continuous mode.
        $cmd = "sudo -u pi -S /home/pi/bin/servo.py -k";
    }
    doCmd($cmd);
}

function setAngle($angle) {
    # Set angle of servo arm.
    $cmd = sprintf(
         "sudo -u pi -S /home/pi/bin/servo.py -a %s",
          $angle);
    doCmd($cmd);
}

function doCmd($cmd) {
    # Run shell command in the background.
    $PID=shell_exec("$cmd > /dev/null 2>&1 & echo $!");
    if(DEBUG == "true") {
        echo "cmd: " . $cmd . "<br>";
        echo "pid: " . $PID . "<br>";
    }
}

?>

</div>
</body>
</html>
