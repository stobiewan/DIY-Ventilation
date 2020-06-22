# ventilation

This repository contains code to run a home ventilation system made up of a controller(raspberry pi), several esp8266
microcontrollers to read temperatures and humidity and control hardware, and any device to view and add inputs through
 a web UI.

The system runs in two major modes, the first is to improve the temperature by moving air from a roof space with closer
temperatures or humidity to the target, and second to transfer air internally from a room closer to the targets to others
when desirable. 

The controller runs an mqtt broker for communication with the esp8266s to control the fan and vales and read sensor
data, a control system to select which actions should be taken, serves a web UI and provides an access point for
microcontrollers and UI to connect to.

mpy-cross is used to compile .mpy's to load onto the esp8266s so they can fit the asynchronous mqtt code. The state
machine uses the transitions package and flask is used for the UI. 
