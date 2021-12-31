<?php
/*
 Script: button.php

 Description: This script executes a server side script
    that creates an empty file with ownership assigned to
    user pi.  This file acts as a flag telling the altimeter
    agent to reset the altimeter to the current barometric
    pressure.

 Note: the following line must be added to the /etc/sudoers
 file so that the www-data user can start this as a process.
 
    www-data ALL=(ALL) NOPASSWD: /home/pi/bin/altimeterReset.sh

 Revision History
   * v10 released 12 Jul 2021 by J L Owrey; first release
*/

# Define global constants

# debug mode
define("_DEBUG", false);
define("_APP_PATH", "/home/pi/bin/altimeterReset.sh");

$cmd = "sudo -u pi -S " . _APP_PATH . " 2>&1";

doCmd($cmd);

function doCmd($cmd) {
    $result = shell_exec($cmd);
    if (_DEBUG) {
        echo "<p>command:<br>" . $cmd . "</p>";
        echo "<p>result:<br>" . $result . "</p>";
    }
    return $result;
}

?>


