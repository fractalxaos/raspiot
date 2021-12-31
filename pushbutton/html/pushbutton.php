<?php
/*
 Script: button.php

 Description: This script starts the push button agent.

 Note: the following line must be added to the /etc/sudoers
 file so that the www-data user can start as a background
 process the push button agent.
 
    www-data ALL=(ALL) NOPASSWD: /home/pi/bin/pushbutton.py

 Revision History
   * v10 released 12 Dec 2021 by J L Owrey; first release
*/

# Define global constants

# debug mode
define("_DEBUG", false);

# Get process id of push button agent process.  If the process is
# not running, no process id will be returned and $processId will
# be an empty string.
$cmd = "ps ax | awk -v a=[p]ushbutton.py '$7 ~ a {print $1}'";
$processId = doCmd($cmd);

# If the process id string is empty then the push button agent
# process is not running, so start it up.
if (sizeOf($processId) == 0) {
    $cmd = "nohup sudo -u pi -S /home/pi/bin/pushbutton.py";
    doCmd("$cmd > /dev/null 2>&1 & echo $!");
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

