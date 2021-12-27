<!DOCTYPE html>
<html>
<head><title>LED Switch</title></head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body {
    background-image: url("../static/chalk.jpg");
}
h2 {
    font: bold 24px arial, sans-serif;
}
#mainContainer {
    width: 270px;
    text-align: center;
    margin: auto;
}
#fmLedState {
    display: block;
    width: 85px;
    text-align: left;
    margin: auto;
    /*border: 1px solid black;*/
}
.infoText {
    display: block;
    text-align: left;
    font: normal 18px arial, sans-serif;
    width: 100%;
    /*border: 1px solid black;*/
}
.radioButtons {
    display: block;
    text-align:left;
    padding-left: 6px;
    /*border: 1px solid black;*/
}
</style>

<body>

<div id="mainContainer">
<h2>LED Control</h2>
<div class="infoText">
Turn on or off an LED connected to the Raspberry Pi GPIO.
</div>
<br>
<form id="fmLedState"
    action="<?php echo htmlspecialchars($_SERVER['PHP_SELF']); ?>"
    method="post">
  <label for="ledstate"><b>LED:</b></label><br>

<?php
    ### Global Constants ####

# LED is connected to GPIO pin 6, which is pin 31 on the
# Raspberry Pi GPIO connector.
define("_GPIO_PIN", '6');
define("DEBUG", false);

# Setup up the GPIO pin the LED is connected to as an
# an output to the LED.
$cmd = sprintf("gpio -g mode %s out", _GPIO_PIN);
doCmd($cmd);

# Read the current state of the GPIO pin to which
# the LED is connected.
$cmd = sprintf("gpio -g read %s", _GPIO_PIN);
$output = doCmd($cmd);
$ledState = $output[0];

# If the user has changed the state of the LED, then
# the user selection determines the state of the LED.
# Otherwise, the led state remains what it was when
# this html document was loaded.
if (isset($_POST["led_state"])) {
  if ($_POST["led_state"] == "on") {
    $ledState = 1;
  } elseif ($_POST["led_state"] == "off") {
    $ledState = 0;
  }
}

# Display the appropriate selections, depending on LED state.
?>

  <div class="radioButtons">
  <input type="radio" id="led_on" name="led_state" value="on"
    <?php if ($ledState == 1) {echo ' checked ';} ?> onchange="setLedState()">
  <label for="led_on">ON</label><br>
  <input type="radio" id="led_off" name="led_state" value="off"
    <?php if ($ledState == 0) {echo ' checked ';} ?> onchange="setLedState()">
  <label for="led_off">OFF</label><br>
  </div>
</form>
</div>
 
<?php
# Write the new LED state to the GPIO pin to which the
# LED is connected.
$cmd = sprintf("gpio -g write %s %s", _GPIO_PIN, $ledState);
doCmd($cmd);

function doCmd($cmd) {
    exec($cmd, $output, $retval);
    if(DEBUG) {
        echo "cmd: " . $cmd . "<br>";
        echo "result: " . $retval . "  ";
        print_r($output); echo "<br>";
    }
    return $output;
}
?>

<script>

function setLedState() {
  /*
   * Whenever the web user changes the on/off selection
   * resubmit this form.
  */
  fmLedState.submit();
}

</script>

</body></html>

