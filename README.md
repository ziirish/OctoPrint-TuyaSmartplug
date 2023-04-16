# OctoPrint-TuyaSmartplug

Work based on [OctoPrint-TPLinkSmartplug](https://github.com/jneilliii/OctoPrint-TPLinkSmartplug) and [python-tuya](https://github.com/clach04/python-tuya).

With this plugin you'll be able to control [Tuya-based](https://en.tuya.com/) SmartPlugs either directly from Octoprint Web interface or through GCODE commands<br>
<br>

## Disclaimer

Tuya is by far the most difficult IoT plataform that can be used to control devices by third-part software like this plugin, they require very specific information on the devices and change often their IoT Cloud Service.<br>
Many user have given up on using Tuya devices with OctoPrint because of its difficulty, some changed to other brands, other dug deeper and changed the device firmware or completely changed the device microcontroler, literally soldering a new one.<br>
If you, like me, only have Tuya devices and doesn't feel confortable on doing firmware flashes or resoldering, this plugin has a place on your OctoPrint instalation and its worth of your time configuring it. <br><br>
This plugin still needs improvements on the code itself, UI, performance and other elements, so you are more then welcome to open [PullRequests](https://github.com/andrelucca/OctoTuya-SmartPlug/pulls) with code updates/fixes or [Issues](https://github.com/andrelucca/OctoTuya-SmartPlug/issues) regarding what needs to be fixed. <br>
This is of course a side project of mine that unites two subjects that I like, so if you open a PR, Issue or a Discussion topic I'll answer as soon as I can, don't be angry if it takes more time than you think it should :). 

## How it was tested?

I tested all the plugin features using my Ender 3 V2 (Using original Marlin as Firmware that I configured and compiled) connected to the Octoprint v1.8.7. The Raspberry of my Octoprint is connected on the PSU of the printer, so if I power of the printer using the Tuya outlet it will also power-off the Raspberry (and will do it unsafely if I hadn't shutdown the Pi OS properly).

## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/ziirish/OctoPrint-TuyaSmartplug/archive/main.zip

## Preparatory Work

All Tuya devices requires 2 infos in order to be controled by other software: `Device ID` and `Local Key`<br>
And this is were the greater difficulty takes place. I made a full guide on how obtain this info in this project [Wiki](https://github.com/ziirish/OctoPrint-TuyaSmartplug/wiki) so make sure you follow it and have this infos before installing an using this plugin.

## Configuration and Settings

All details on how to configure the plugin and how to change its settings according to your liking are in this project [Wiki](https://github.com/ziirish/OctoPrint-TuyaSmartplug/wiki)

## Support jneilliii Efforts
Most of the code used in this plugin has been written by
[jneilliii](https://github.com/jneilliii) so if you want to support someone,
you can support his work.
