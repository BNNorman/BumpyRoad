i# Logger.py
#
# Adafruit CircuitPython 8.0.0-beta.6 on 2022-12-21; Raspberry Pi Pico W with rp2040
#
# Records GPS, Speed, Track ,Accel, Gyro readings at 10 readings per second
#

import adafruit_gps
import sdcardio
import adafruit_mpu6050
import digitalio
import board
import busio
import storage
import os
import time
import sys
import rtc
import neopixel_write
import adafruit_logging as logging
from file_handler import FileHandler
from neocolours import *


LOOP_PERIOD=0.1     # seconds between reading samples
SD_CACHE_LIMIT=10   # number of readings to cache before writing to SD
LOG_FILE="/sd/Track.log"

# Pins used
SDA=board.GP4 # accelerometer
SCL=board.GP5
TX=board.GP8 # GPS
RX=board.GP9
GPS_BAUD=9600
CS=board.GP13 # SD card SPI
SCK=board.GP10
MOSI=board.GP11
MISO=board.GP12
NEO_PIN=board.GP28 # pico doesn't have a board.NEOPIXEL
LED_PIN=board.LED

led = digitalio.DigitalInOut(LED_PIN)
led.direction = digitalio.Direction.OUTPUT
led.value=False

def errorBlink(colour,msg=None):
    if msg is not None:
        print(msg)
    while True:
        neoBlink(colour)

# setup neopixel for progress indication
neo_pin = digitalio.DigitalInOut(NEO_PIN)
neo_pin.direction = digitalio.Direction.OUTPUT
neo_colour=None

# neoBlink turns the neopixel on or off
# used when waiting for GPS fix and time/date
def neoBlink(colour):
    global neo_colour
    if neo_colour!=colour:
        setNeoPixel(colour)
        time.sleep(0.5)
    else:
        setNeoPixel(BLACK)
        time.sleep(0.5)

def setNeoPixel(colour):
    global neo_colour
    neopixel_write.neopixel_write(neo_pin, colour)
    neo_colour=colour
    
# flash 5 times to show we are starting
for i in range(5):
    neoBlink(CYAN)

setNeoPixel(BLACK)

# setup the SD card
spi = busio.SPI(board.GP10, board.GP11, board.GP12)

# try to access the SD card so we can do logging
try:
    sd = sdcardio.SDCard(spi, CS)
    vfs = storage.VfsFat(sd)
    storage.mount(vfs, '/sd')
    dirList=os.listdir('/sd')
except Exception as e:
    led.value=False
    errorBlink(MAGENTA,e)

# setup the GPS
uart = busio.UART(TX, RX, baudrate=GPS_BAUD)
gps=adafruit_gps.GPS(uart)

# setup the MPU6050
i2c = busio.I2C(SCL,SDA)  # I2C1 SCL SDA, not defined on Pico W
mpu=adafruit_mpu6050.MPU6050(i2c)


brfn=None # BumpyRoad data log filename

monotonic_start=None # used to control data sample loop

class RTC(object):
    # note default time is overwritten when GPS gets a time lock
    def __init__(self,now=(2023,1,17,19,41,0,0,0,0)):
        self.now=now   
    @property
    def datetime(self):
        return time.struct_time(self.now)

def createCSVheaders():
    # MUST be called after gps fix
    global gps,brfn

    if brfn is None:
        dt=gps.datetime
        brfn=f"/sd/{dt.tm_mday:02d}{dt.tm_mon:02d}{dt.tm_year%100}{dt.tm_hour:02d}{dt.tm_min:02d}{dt.tm_sec:02d}.csv"
    
    with open(brfn,"w") as file:
        file.write("lat,lon,datetime,time_monotonic,speed_knots,track_deg,GyZ,GyY,GyX,Tmp,AcZ,AcY,AcX\r\n")

cache=[]  # I am going to cache a number of readings to reduce SDcard accesses 

def saveData(force=False):
    global gfn,mpu,gps,cache,SD_CACHE_LIMIT,monotonic_start
    
    GyX,GyY,GyZ=mpu.gyro
    AcX,AcY,AcZ=mpu.acceleration
    
    # dt includes commas when included in a string and that messes up the CSV
    dt=gps.datetime
    dts=f"{dt.tm_mday:02d}/{dt.tm_mon:02d}/{dt.tm_year%100} {dt.tm_hour:02d}:{dt.tm_min:02d}:{dt.tm_sec:02d}"
    
    # this method can be called several times per second so time.monotonic() gives a finer
    # resolution so we start when we first cache data and only store the difference between now
    # and monotonic_start.
    
    if monotonic_start is None:
        monotonic_start=time.monotonic()
    
    cache.append(f"{gps.latitude},{gps.longitude},{dts},{time.monotonic()-monotonic_start},{gps.speed_knots},{gps.track_angle_deg},{GyZ},{GyY},{GyX},{mpu.temperature},{AcZ},{AcY},{AcX}\r\n")
    
    if (len(cache)>=SD_CACHE_LIMIT) or force:
        try:
            with open(brfn,"a") as file:
                for line in cache:
                    file.write(line)
                cache=[]

        except Exception as e:
            errorBlink(YELLOW,f"Exception recording data: {e}")

def runLoop():
    global gps,LOOP_PERIOD
    
    setNeoPixel(GREEN) # solid green indicates we are all go
            
    while True:
        loop_start=time.monotonic()
        saveData()
        gps.update()
        while (time.monotonic()-loop_start)<LOOP_PERIOD:
            gps.update()
   
###################################

while not gps.has_fix:
    neoBlink(RED)
    gps.update()
    
setNeoPixel(BLACK)
    
# gps may have to read a number of sentences after the fix to get the
# correct datetime (localtime) which is needed to ensure log files have valid names
# and creation dates
while gps.datetime.tm_year==0: # year is usually the last part to arrive
    neoBlink(YELLOW)
    gps.update()

setNeoPixel(BLACK)

tsrc=RTC((2023,1,17,19,41,0,0,0,0)) # any old timestamp for now
rtc.set_time_source(tsrc)

r=rtc.RTC()
r.datetime=gps.datetime # set the localtime

# all set lets go
    
createCSVheaders()

try:
    runLoop()
    
except Exception as e:
    saveData(True)
    storage.umount("/sd")
    storage.enable_usb_drive()
    errorBlink(CYAN,f"Terminated - Exception {e}")
