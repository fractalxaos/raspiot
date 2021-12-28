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

   ### CONSTANTS ###

    ### Global Variables ###

$waveform = $_POST["waveform"];
$frequency = $_POST["freqSet"];
$amplitude = $_POST["ampSet"];
$dutyCycle = strval((float)$_POST["dutySet"] / 100.0);
$runState = $_POST["runState"];
$debugMode = $_POST["debugMode"];

if($debugMode == "true") {
    echo "<div class=\"debugInfo\">";
}

if($runState == "off") {
    $cmd = "sudo -u pi -S /home/pi/bin/fncgen.py -k";
} else {
    $cmd = sprintf(
        "sudo -u pi -S /home/pi/bin/fncgen.py -w %s -f %s -a %s -d %s",
        $waveform, $frequency, $amplitude, $dutyCycle
        );
}

$PID=shell_exec("nohup $cmd > /dev/null 2>&1 & echo $!");

if($debugMode == "true") {
    echo "cmd: " . $cmd . "<br>";
    echo "pid: " . $PID . "<br>";
    echo "</div>";
}
?>
</body>
</html>

