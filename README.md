# BumpyRoad

A CircuitPython program to record GPS and accelerometer readings whilst driving. I was asked, a long time ago if I could do this and, initially, I created an Arduino program running on a NodeMCU ESP32 but thought I'd like to have a go at doing this in Python.

Whilst trying Micropython on the NodeMCU I encountered SD Card issues, during development, whch caused me to switch to a Pico W and CircuitPython. Anyway, the fact that CircuitPython mounts its devices into the Windows filesystem was another BIG plus.

The project uses a cheap SD card, a common Ublox NEO6M and an MPU6050 accelerometer plus a cheap active GPS antenna. The latter has a magnetic base and can be placed on the roof of a car. The GPS is significantly improved using it. With just the ceramic antenna which comes with the GPS I found the coordinates wandering into fields, when I mapped the coordinates using Jupyter, whilst I knew I was on a road. So, that was no good for pin pointing the section of road with nasty bumps in it.

If you want to run this at power on you need to replace the code.py file with Logger.py


# CircuitPython

Available from https://circuitpython.org/downloads

The version used for this was:-

Adafruit CircuitPython 8.0.0-beta.6 on 2022-12-21; Raspberry Pi Pico W with rp2040

## /lib

The CircuitPython libraries required are all available in the downloadable CircuitPython V8 bundle.

* adafruit_register
* adafruit_gps
* adafruit_mp6050
* adafruit_sdcard
* adafruit_ticks

# Prototype

The prototype was built on vero-stripboard shown below.


![IMG_20230128_143235](https://user-images.githubusercontent.com/15849181/215272289-30839ee6-524e-40f4-b216-fa6af5046d79.jpg)
