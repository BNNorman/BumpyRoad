import adafruit_gps
import adafruit_sdcard
import adafruit_mpu6050
import digitalio
import board
import busio
import storage
import os
import time
import sys
import rtc

LOOP_PERIOD=0.1     # seconds between reading samples
SD_CACHE_LIMIT=10   # number of readings to cache before writing to SD

SDA=board.GP4
SCL=board.GP5
TX=board.GP8
RX=board.GP9
GPS_BAUD=9600
LED=board.LED
CS=board.GP13
SCK=board.GP10
MOSI=board.GP11
MISO=board.GP12

# set up SD card for logging
cs=digitalio.DigitalInOut(CS)
cs.direction=digitalio.Direction.OUTPUT
cs.value=True

spi = busio.SPI(board.GP10, board.GP11, board.GP12) # cytron board
sd = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sd)
storage.mount(vfs, '/sd')


# setup the indicator led
# I'm going to blink this
led = digitalio.DigitalInOut(LED)
led.direction=digitalio.Direction.OUTPUT
led.value=True

# check the SDcard is present
try:
    print("/sd files:",os.listdir('/sd'))
except Exception as e:
    print(f"Exception accessing SD card with listdir: {e}")
    sys.exit()
    
# setup the GPS
uart = busio.UART(TX, RX, baudrate=GPS_BAUD)
gps=adafruit_gps.GPS(uart)

# setup the MPU6050
i2c = busio.I2C(SCL,SDA)  # I2C1 SCL SDA, not defined on Pico W
mpu=adafruit_mpu6050.MPU6050(i2c)


gfn=None
monotonic_start=None

def createCSVheaders():
    # MUST be called after gps fix
    global gps,gfn

    if gfn is None:
        dt=gps.datetime
        gfn=f"/sd/{dt.tm_mday:02d}{dt.tm_mon:02d}{dt.tm_year%100}{dt.tm_hour:02d}{dt.tm_min:02d}{dt.tm_sec:02d}.csv"
    
    with open(gfn,"w") as file:
        file.write("lat,lon,datetime,time_monotonic,speed_knots,track_deg,GyZ,GyY,GyX,Tmp,AcZ,AcY,AcX\r\n")

cache=[]  # I am going to cache a number of readings to reduce SDcard accesses 

def saveData(force=False):
    global gfn,mpu,gps,cache,SD_CACHE_LIMIT,monotonic_start
    
    #print("Caching data")
    
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
            #print("Appending cache to file")
            with open(gfn,"a") as file:
                for line in cache:
                    file.write(line)
                cache=[]
            #print("Finished appending")
        except Exception as e:
            print(f"Exception recording data: {e}")

def runLoop():
    global gps,LOOP_PERIOD
    
    while True:
        led.value=not led.value
        loop_start=time.monotonic()
        saveData()
        while (time.monotonic()-loop_start)<LOOP_PERIOD:
            gps.update()
   
###################################
  
print("Waiting for gps fix")
while not gps.has_fix:
    led.value=not led.value
    gps.update()
    
# gps may have to read a number of senetences after the fix to get the
# correct datetime (localtime)
print("Waiting for datetime")
while gps.datetime.tm_year==0:
    led.value=not led.value
    gps.update()
    
r=rtc.RTC()
r.datetime=gps.datetime # set the localtime

createCSVheaders()
   
try:
    runLoop()
    
except:
    led.value(False)
    saveData(True)
    storage.umount("/sd")
