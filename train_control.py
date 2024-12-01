# -*- coding: utf-8 -*-
"""
Created on Tue Nov 28 21:41:49 2023

@author: davida
"""
import asyncio
from bleak import BleakClient
import time
import random
import numpy
import datetime


#--- running parameters -------------------------------------------------------

#operator switching time
opSwitchTime=1.5

#horn info
#https://www.trains.com/trn/train-basics/abcs-of-railroading/whistle-signals/
#long horn blast [s]
longHornTime=1.5
#short horn blast [s]
shortHornTime=0.5
#time between horn blasts [s]
hornSpaceTime=0.3

#speed for bell ringing to start/stop when accelerating or decelerating
bellSpeed=5

#maximum train speeds
maxSpeedList=[7,11,15]

#train acceleration pause
accelTimeDelay=1

#max travel time (s)
maxTravelTime=120
#min travel time (s)
minTravelTime=60

#max pause time (s)
maxPauseTime=45
#min pause time (s)
minPauseTime=30

#reverse speed list
reverseSpeeds=list(range(bellSpeed))
reverseSpeeds.pop(0)

#reverse timing
#run
maxRevRunTime=40
minRevRunTime=20

#pause
maxRevPauseTime=15
minRevPauseTime=10

#------------------------------------------------------------------------------

#bluetooth connection details
address = "44:A6:E5:3E:2E:CB"
UUID="08590f7e-db05-467e-8757-72f6faeb13d4"

#train command functions
#this commends sends any general command to the train as defined by functions below
async def send_cmd(client, values):
        checksum = 256
        for v in values:
            checksum -= v;
        while checksum<0:
            checksum+=256
        values.insert(0,0)
        values.append(checksum)
        await client.write_gatt_char(UUID, bytes(values))
        
async def set_speed(client,speed):
        await send_cmd(client,[0x45, speed])
        print('Speed: ',speed)
        
async def blow_horn(client,message):
    print('Horn is blowing for '+message)
    
    if message == 'brakes released':
        #two long blasts
        for i in range(2):
            await send_cmd(client,[0x48, 1])
            time.sleep(longHornTime)
            await send_cmd(client,[0x48, 0])
            if i<2:
                time.sleep(hornSpaceTime)
    
    elif message == 'stopped':
        #one long blast
        await send_cmd(client,[0x48, 1])
        time.sleep(longHornTime)
        await send_cmd(client,[0x48, 0])
        
    elif message == 'crossing':
        #two long blasts
        for i in range(2):
            await send_cmd(client,[0x48, 1])
            time.sleep(longHornTime)
            await send_cmd(client,[0x48, 0])
            time.sleep(hornSpaceTime)
        
        #one short blast
        await send_cmd(client,[0x48, 1])
        time.sleep(shortHornTime)
        await send_cmd(client,[0x48, 0])
        time.sleep(hornSpaceTime)
        
        #one long blast
        await send_cmd(client,[0x48, 1])
        time.sleep(longHornTime)
        await send_cmd(client,[0x48, 0])
    
        
async def ring_bell(client):
    print('Bell is ringing')
    await send_cmd(client, [0x47, 1])
    
    
async def ring_bell_off(client):
    print('Bell ringing is stopped')
    await send_cmd(client, [0x47, 0])

async def accelerate_train(client,startSpeed,endSpeed):
    speed = startSpeed
    if speed == 0 and endSpeed > startSpeed:
        await ring_bell(client)
        time.sleep(opSwitchTime)
        await blow_horn(client, 'brakes released')
        time.sleep(opSwitchTime)
    while speed != endSpeed:
        await set_speed(client,speed)
        if speed > endSpeed:
            speed -= 1
            if speed == bellSpeed-1:
                await ring_bell(client)
        else:
            speed += 1
            if speed == bellSpeed+1:
                await ring_bell_off(client)
        time.sleep(accelTimeDelay)
    
    await set_speed(client,endSpeed)
    
    if speed == 0 and startSpeed > endSpeed:
        time.sleep(opSwitchTime)
        await ring_bell_off(client)
        time.sleep(opSwitchTime)
        await blow_horn(client,'stopped')
        
async def set_reverse(client, on):
        if on:
            print('Train is in reverse mode')
        else:
            print('Train is in forward mode')
        await send_cmd(client,[0x46, 0x02 if on else 0x01])

async def travel_time(travelTime):
    #time.sleep(travelTime)
    await asyncio.sleep(travelTime)
    
async def rr_crossing(client,crossingTimeDelay):
    #initialize
    currentInterval=0
    nextInterval=0
    #print('In the rr_crossing function')
    shortestTime=longHornTime*3+shortHornTime+hornSpaceTime*3+5
    if crossingTimeDelay:
        crossingTimeDelay.insert(0,0)
        #print(crossingTimeDelay)
        for i in range(len(crossingTimeDelay)-1):
            currentInterval+=crossingTimeDelay[i]
            nextInterval+=crossingTimeDelay[i+1]
            #print('i = '+str(i))
            #print('Current Interval is '+str(currentInterval))
            #print('Next Interval is '+str(nextInterval))
            #time.sleep(crossingTimeDelay[i])
            #print('Timing for crossing '+str(i+1)+' started')
            await asyncio.sleep(crossingTimeDelay[i+1])
            timeBetween=nextInterval-currentInterval
            #print('Time between crossing '+str(i)+' and crossing '+str(i+1)+': '+str(timeBetween)+' sec')
            if timeBetween > shortestTime:
                await blow_horn(client, 'crossing')  
            else:
                print('Crossing '+str(i+1)+' skipped due to timing constraints.')
        
def calc_crossing_times(travelTime):
    #initialize
    crossingTimeDelay=[]
    
    #number of crossings
    numCrossings=random.choice([0,1,2,3,4,5])
    
    if numCrossings>0:
        meanCrossingInterval=travelTime/(numCrossings+1)
        #populate the crossing delay list
        for i in range(numCrossings):
            crossingTimeDelay.append(numpy.random.normal(meanCrossingInterval,(2*meanCrossingInterval)/12))
            print('Crossing '+str(i+1)+' at: '+str(sum(crossingTimeDelay)))
    else:
        print('No RR Crossings on this route.')
    
    return crossingTimeDelay

# *** MAIN ***
#initialize settings, volumne

#run outer loop - contains a random set of forward loops, followed by a reverse

#run forward loop
#bell about to starting to move
#horn two long blasts (--), brakes released proceed
#accelerate
#bell off at speed ?
#travel
#horn crossing --.-
#decelerate
#bell on at speed ?
#bell off at speed 0
#horn -, stopped, air brakes applied, pressure equalized
#pause for stop for ??? time


#run reverse

#main async function
async def main():
    client = BleakClient(address)
    try:
        await client.connect()
        #---------- Loops that control running time ----------
        #for loop for explicit control
        #while loop to shut down at a specific time
        for j in range(1): #this could be a while loop
        #datetime.now().hour gives output in 24-h time format
        #while datetime.datetime.now().hour < 12:
            numFwdLoops=random.choice([3,4,5])
            print('Program will run '+str(numFwdLoops)+' forward loops')
            for i in range(numFwdLoops):
                #generate route travel time
                travelTime=numpy.random.normal(numpy.average([minTravelTime,maxTravelTime]),(maxTravelTime-minTravelTime)/12)
                pauseTime=numpy.random.normal(numpy.average([minPauseTime,maxPauseTime]),(maxPauseTime-minPauseTime)/12)
                print('Travel time is '+str(travelTime)+' sec')
                print('Time at stop is '+str(pauseTime)+' sec')
                #deterine the number of RR crossings and their times on the route
                crossingTimeDelay=calc_crossing_times(travelTime)
                #determine the maximum speed for the route
                maxSpeed=random.choice(maxSpeedList)
                print('Maximum speed for the route is '+str(maxSpeed))
                
                await set_reverse(client, False)
                await accelerate_train(client, 0, maxSpeed)
                await asyncio.gather(travel_time(travelTime),rr_crossing(client, crossingTimeDelay))
                await accelerate_train(client, maxSpeed, 0)
                #pause to pick up passengers, cargo, or engine supplies
                print('Waiting at the stop')
                time.sleep(pauseTime)
            
            #turn reverse on
            reverseTime=numpy.random.normal(numpy.average([minRevRunTime,maxRevRunTime]),(maxRevRunTime-minRevRunTime)/12)
            reversePauseTime=numpy.random.normal(numpy.average([minRevPauseTime,maxRevPauseTime]),(maxRevPauseTime-minRevPauseTime)/12)
            revMaxSpeed=random.choice(reverseSpeeds)
            print('Reverse travel time is '+str(reverseTime)+' sec')
            print('Time to get moving forward '+str(reversePauseTime)+' sec')
            print('Maximum speed for the route is '+str(revMaxSpeed))
            await set_reverse(client, True)
            await accelerate_train(client, 0, revMaxSpeed)
            #a glitch shuts off the bell at reverse speeds starting at 2 up to bellSpeed
            #this call hacks around it
            #bell times out, need to measure the period
            await ring_bell(client)
            time.sleep(reverseTime)
            await accelerate_train(client, revMaxSpeed, 0)
            await set_reverse(client, False)
            #pause to get the train moving forward again
            print('Waiting to get the train moving forward again')
            time.sleep(reversePauseTime)
        
            
    
    except Exception as e:
        print(e)
    finally:
        await client.disconnect()
        
#main program
try:
    loop = asyncio.get_running_loop()
except RuntimeError:  # 'RuntimeError: There is no current event loop...'
    loop = None

if loop and loop.is_running():
    print('Async event loop already running. Adding coroutine to the event loop.')
    tsk = loop.create_task(main())
    # ^-- https://docs.python.org/3/library/asyncio-task.html#task-object
    # Optionally, a callback function can be executed when the coroutine completes
    # tsk.add_done_callback(
    #     lambda t: print(f'Task done with result={t.result()}  << return val of main()'))
else:
    print('Starting new event loop')
    result = asyncio.run(main())