<!-- Courtsey ruler
2345678901234567890123456789012345678901234567890123456789012345678901234567890
-->
<html>
<head>
<meta charset="UTF-8">
<style>
.debugInfo {
    width: 100%;
    font: normal 12px arial, sans-serif;
    text-align: left;
    margin: auto;
}
</style>
</head>
<body>

<?php
/*
 Script: fncgen.php

 Description: This script executes the servo python script
 'fncgen.py'.

 Note: the following line must be added to the /etc/sudoers
 file so that the www-data user can start as a background
 process the servo.py python script.
 
    www-data ALL=(ALL) NOPASSWD: /home/pi/bin/fncgen.py

 Revision History
   * v10 released 12 Dec 2021 by J L Owrey; first release
*/

    ### Global Variables ###

$waveform = $_POST["waveform"];
$frequency = $_POST["freqSet"];
$amplitude = $_POST["ampSet"];
$dutyCycle = strval((float)$_POST["dutySet"] / 100.0);
$runState = $_POST["runState"];
$debugMode = $_POST["debugMode"];

if($debugMode == "true") {
    # Create an HTML element to display debug data.
    echo "<div class=\"debugInfo\">";
}

# Set function generator state based on user input from web page.
if($runState == "off") {
    # Kill all instances of the function generator.
    $cmd = "sudo -u pi -S /home/pi/bin/fncgen.py -k";
} else {
    # Start up the function generator with the parameters submitted
    # by the web page.
    $cmd = sprintf(
        "sudo -u pi -S /home/pi/bin/fncgen.py -w %s -f %s -a %s -d %s",
        $waveform, $frequency, $amplitude, $dutyCycle
        );
}

# Run the command in the background.
$PID=shell_exec("nohup $cmd > /dev/null 2>&1 & echo $!");

if($debugMode == "true") {
    echo "cmd: " . $cmd . "<br>";
    echo "pid: " . $PID . "<br>";
    echo "</div>";
}
?>
</body>
</html>

