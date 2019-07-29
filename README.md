# climatecontrol
Home Assistant / AppDaemon climate control App

A AppDaemon App to control the climate in our house.
Uses Google Calendar to schedule temperatures and learns heat / cool times so as to start and finish in time.

Initial simple approach:

 * configuration through 'zones': named groups of one or more 'controls'
 * when a calendar event triggers (state -> 'on'), set temperature on the relevant controls and switch them on
 * message (summary) of the calendar event should start with the name of the zone, followed by a temperature
 * schedule to switch off the controls at the end of the calendar event
 * when a change is happening to any of the referred controls, test if the boiler should be on or off and set the boiler target
 * every minute check the current boiler state against the target and potentially toggle the boiler

Currently starts with all controls and boiler switched off, as well as the boiler target.
Should read the relevant portion of the calendar at start-up and set the state and schedule accordingly.