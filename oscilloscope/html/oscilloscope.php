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
 Script: oscilloscope.php

 Description: This script starts the ADC data acquisition agent.

 Note: the following line must be added to the /etc/sudoers
 file so that the www-data user can start this process.
 
    www-data ALL=(ALL) NOPASSWD: /home/pi/bin/oscilloscope.py
 
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
   * v10 released 11 Nov 2021 by J L Owrey; first release
*/

# Define global constants

$sampleSize = $_POST["sampleSize"];
$sampleRate = $_POST["sampleRate"];
$acqState = $_POST["acqState"];
$debugMode = $_POST["debugMode"];

if($debugMode == "true") {
    echo "<div class=\"debugInfo\">";
}

if($acqState == "run") {
    # Start up new instance of oscilloscope.py process.
    $cmd = sprintf(
        "sudo -u pi -S /home/pi/bin/oscilloscope.py -n %s -r %s",
        $sampleSize, $sampleRate
        );
} else {
    $cmd = "sudo -u pi -S /home/pi/bin/oscilloscope.py -k";
}

doCmd("nohup $cmd > /dev/null 2>&1 & echo $!");

# Run command and echo result if in debug mode.
function doCmd($cmd) {
    GLOBAL $debugMode;
    exec($cmd, $output, $retval);
    if($debugMode == "true") {
        echo "cmd: " . $cmd . "<br>";
        echo "result: " . $retval . "  ";
        print_r($output);
    }
    return $output;
}
?>
</body>
</html>


