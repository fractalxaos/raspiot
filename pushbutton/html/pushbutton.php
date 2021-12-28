<?php
/*
 Script: button.php

 Description: This script starts the push button agent.
 Revision History
   * v10 released 11 Jan 2021 by J L Owrey; first release
*/

# Define global constants

# debug mode
define("_DEBUG", false);
define("_AGENT_PATH", "/home/pi/bin/pushbuttonAgent.py");

if (_DEBUG) {
    $user = shell_exec('whoami');
    echo "user: " . $user;
    echo "<br><br>";
}

# Get process id of pushbutton agent process.
$cmd = "ps ax | awk -v a=[p]ushbutton.py '$7 ~ a {print $1}'";
$processId = doCmd($cmd);

if (sizeOf($processId) == 0) {
    #echo "<h4>Starting up pushbutton agent</h4>";
    $cmd = "sudo -u pi -S /home/pi/bin/pushbutton.py";
    $cmd = "nohup $cmd > /dev/null 2>&1 & echo $!";
    doCmd($cmd);
}

function doCmd($cmd) {
    exec($cmd, $output, $retval);
    if(_DEBUG) {
        echo "cmd: " . $cmd . "<br>";
        echo "result: " . $retval . "  ";
        print_r($output); echo "<br>";
    }
    return $output;
}
?>

