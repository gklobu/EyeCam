#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Part of the Human Connectome - Lifespan Project Task fMRI Battery
***************************************************************************************************************
Script to display fixation cross to participant while recording eye video via frame grabber
or webcam (tested with Epiphan DVI2USB 3.0)

Displays real-time Eyelink video for RA on main monitor
***************************************************************************************************************
For use during resting state and ASL scans for the Lifespan Human Connectome Project
Requires 2 CPU cores
Works best with at least 8 GB of RAM and SSD hard drive (for faster video output)
***************************************************************************************************************

Tested on a Macbook Pro (OS 10.11.6) and a Macbook Air (OS 10.12.2)
Gian Klobusicky, Leah H Somerville
gklobusicky@fas.harvard.edu
02/20/2017
***************************************************************************************************************
Tested with Psychopy 1.83.04 and 1.84.02
  Peirce, JW (2007) PsychoPy - Psychophysics software in Python. Journal of Neuroscience Methods, 162(1-2), 8-13.
  Peirce, JW (2009) Generating stimuli for neuroscience using PsychoPy. Frontiers in Neuroinformatics, 2:10. doi: 10.3389/neuro.11.010.2008
***************************************************************************************************************
"""
from ctypes import c_bool
import datetime
from multiprocessing import Process, Queue, Value
import numpy as np
import os
import pandas as pd
from psychopy import visual, core, event, logging, gui, monitors
import pyglet
from subprocess import check_output
import sys
import yaml
import cv2 #try to import with others


#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Params
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# Ensure that relative paths start from the same directory as this script
_thisDir = os.path.dirname(os.path.abspath(__file__)).decode(
    sys.getfilesystemencoding())
os.chdir(_thisDir)
# RA's screen (for eye video monitor; 0=primary, 1=secondary and should usually be 0):
raScreen = 0
# Frame rate (for recording):
vid_frame_rate = 30
# Key that ends experiment:
quitKey = 'escape'
# Video encoding:
vidExt = '.mp4'
# Timestamp Format
timestampFormat = '%a %b %d %H:%M:%S %Y'

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Basic experiment setup
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::


endExpNow = False  # flag for 'escape' or other condition => quit the exp


# Load Site-configurable parameters
def loadConfiguration(configFile):
    if os.path.exists(configFile):
        with open(configFile) as f:
            config = yaml.safe_load(f)
    else:
        copyMsg = ('Please copy configuration text file ' +
                   '"%s.example" to "%s" ' % tuple([os.path.basename(configFile)] * 2) +
                   'and edit it with your trigger and buttons.')
        raise IOError(copyMsg)
    return config


config = loadConfiguration('siteConfig.yaml')

# Display Information
display = pyglet.window.get_platform().get_default_display()
screens = display.get_screens()
if config['monitor']['screen'] >= len(screens):
    pScreen = 0
else:
    pScreen = config['monitor']['screen']

#dims for participant screen (ra screen set below):
resolution = [screens[pScreen].width, screens[pScreen].height]

mon = monitors.Monitor('newMonitor')
mon.setWidth(config['monitor']['width'])
mon.setDistance(config['monitor']['distance'])
mon.setSizePix(resolution)

# Set HCP Style Params
triggerKey = config['trigger']  #5 at Harvard
titleLetterSize = config['style']['titleLetterSize']  # 3
textLetterSize = config['style']['textLetterSize']  # 1.5
fixLetterSize = config['style']['fixLetterSize']  # 2.5
wrapWidth = config['style']['wrapWidth']  # 30
subtitleLetterSize = config['style']['subtitleLetterSize']  # 1
verbalColor = config['style']['verbalColor'] #  '#3EB4F0'



#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Instruction screen function
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def instruct(expName):
    # Setup the RA Experimenter Window
    raWin = visual.Window(size=[1100,675], fullscr=False, allowGUI=True, allowStencil=False,
                          monitor=u'testMonitor', color=u'black', colorSpace='rgb',
                          blendMode='avg', useFBO=True,
                          units='deg',
                          screen=raScreen)
    introText = visual.TextStim(win=raWin, ori=0, name='introText',
                                text=expName+'SCAN', font='Arial',
                                pos=[0, 0], height=titleLetterSize, wrapWidth=30,
                                color='white', colorSpace='rgb', opacity=1,
                                depth=-1.0)
    #Create text object to hold instructions:
    raText = visual.TextStim(win=raWin, ori=0, name='raText',
                             text='', font='Arial',
                             pos=[0, -4.5], height=textLetterSize, wrapWidth=30,
                             color='white', colorSpace='rgb', opacity=1,
                             depth=0.0)
    raVerbalText = visual.TextStim(win=raWin, ori=0, name='raVerbalText',
                                   text='', font='Arial',
                                   pos=[0,3], height=1.5, wrapWidth=30,
                                   color=verbalColor, colorSpace='rgb', opacity=1,
                                   depth=0.0, italic=True)

    outerFrame = visual.Rect(win=raWin, lineWidth=1, lineColor='white',
                             width=35, height=23, units='deg', name='outerFrame')

    #Update RA text (i.e., instructions read to participant over intercom):
    verbal1Msg = (
        '"In the next scan all you are going to see is a white plus sign '
        'in the middle of the screen. Your job is to simply rest, keep '
        'your eyes open, and look at the plus sign during the entire '
        'scan. You can blink normally, and you do not have to think about '
        'anything in particular.')

    verbal2Msg = (
        'However, it is very important that you do not fall asleep, '
        'and as always, that you stay very still from beginning to end.'
        '\n\nDoes that make sense? Do you have any questions? Are you '
        'ready to begin?"')

    raVerbalText.text = verbal1Msg
    raText.text = 'Press <space> to continue.'
    raVerbalText.draw()
    raText.draw()
    raWin.flip()
    raWin.winHandle.activate()
    loopOver = False
    npresses = 0
    while not loopOver:
        inkeys = event.getKeys()
        if 'space' in inkeys:
            npresses += 1
            if npresses == 1:
                raVerbalText.text = verbal2Msg
                raText.text = 'Press <space> to continue.'
                raVerbalText.draw()
                raText.draw()
                raWin.flip()
            else:  # Second <space> press
                loopOver = True
                raText.pos = [0, 0]
        elif quitKey in inkeys:
            endExpNow = True
            core.quit()
            loopOver = True
    return raWin


#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Image cropping function
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def reFrame(fr, aperture):
    return fr[aperture[0]:aperture[1], aperture[2]:aperture[3], :]


#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Present fixation, leave it up until script ends
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def fixCross(win, cross):
    cross.draw(win)
    win.mouseVisible = False
    win.flip()
    logging.info('Begin Fixation Cross')


#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Wait for scanner trigger
#Returns trigger timestamp
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def waitForTrigger(clocks):
    # Inputs: Psychopy Clock to reset when trigger is received.
    # Returns: core timer and wall time of trigger
    event.clearEvents() #Flush keys
    trigger_ts = core.getTime()
    loopOver = False
    event.getKeys() #clear any pre-existing keypresses before beginning to wait
    while not loopOver:
        inkeys = event.getKeys()
        if triggerKey in inkeys:
            trigger_ts = core.getTime()  # time stamp for start of scan
            triggerWallTime = datetime.datetime.today()  # Wall Time timestamp
            loopOver = True
            for clock in clocks:
                clock.reset()  # Zero the countdown clock
        elif quitKey in inkeys:
            endExpNow = True
            core.quit()
            loopOver = True
    triggerMsg = 'Trigger received at %s' % triggerWallTime.strftime(timestampFormat)
    print(triggerMsg)
    logging.info(triggerMsg)
    return trigger_ts, triggerWallTime



#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Countdown (for consistency w/ other scripts)
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def count_down(win, cap=None, aperture=None, timestamps=None, clock=None):
    # Create images for Routine "countdown"
    # To record images during the countdown, provide the cv VideoCapture instance, an aperture 
    # (or None) to reframe the recorded image, a list of timestamps to append times to, and a 
    # psychopy Clock to read times from.
    counter = visual.TextStim(win=win,
                              ori=0,
                              name='countdownText',
                              text='4',
                              font='Arial',
                              pos=[0, 0],
                              height=titleLetterSize,
                              wrapWidth=None,
                              color='white',
                              colorSpace='rgb',
                              opacity=1,
                              depth=-3.0)
    for this_one in range(4, 0, -1):
        counter.setText(str(this_one))
        counter.draw(win)
        win.flip()
        flip_time = core.getTime()
        win.mouseVisible = False
        while core.getTime() - flip_time < 2:
            if cap:
                recFrame(cap, aperture=aperture)
                timestamps.append(clock.getTime())
            if event.getKeys(keyList=[quitKey]):
                core.quit()
                break


#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Video writing function
#To be run in parallel with data collection loop in main
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def writeVid(update_queue, quit_flag, thisRun, out_file):
    #CV2 does not like to run in two processes simultaneously:
    import imageio
    #Create video writer object:
    out = imageio.get_writer(out_file, fps=vid_frame_rate)
    while not quit_flag.value:
        #Keep popping and writing frames:
        out.append_data(update_queue.get())
    #Finishes file IO when quit_flag is flipped to True:
    out.close()


#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Get Task version from VERSION file or git
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def gitVersion():
    try:
        revision = check_output(['git', 'rev-parse', '--short', 'HEAD'])
        revision = revision.strip()
    except:
        if os.path.exists('VERSION'):
            with open('VERSION', 'r') as f:
                revision = f.read().strip()
        else:
            revision = ''
    return revision

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#User input #def scan initialize
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def scanInit():
    expInfo = {'scan type': ['SELECT SCAN TYPE', 'REST', 'mbPCASL'],
            'age': u'',
            'sessionID': u'',
            'runNumber': '1',
            'test mode': False}
    dlg = gui.DlgFromDict(dictionary=expInfo, title='Eye Cam')
    if dlg.OK == False: core.quit()  # user pressed cancel
    expInfo['date'] = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    if expInfo['scan type'] == 'SELECT SCAN TYPE':
        raise ValueError('CHOOSE A SCAN TYPE!!!')
    else:
        expName = expInfo['scan type']

    expInfo['expName'] = expName

    # Data file name stem = absolute path + name; later add .psyexp, .csv, .log, etc
    filebase = _thisDir + os.sep + u'data' + os.sep + '_'.join([expName, expInfo['sessionID']])
    if not os.path.isdir(os.path.dirname(filebase)):
        os.makedirs(os.path.dirname(filebase))

    #save a log file for detail verbose info
    #put in initializer
    logFile = logging.LogFile(filebase + '_%s.log' % expInfo['date'], level=logging.INFO)
    logging.console.setLevel(logging.WARNING
                         )  # this outputs to the screen, not a file

    #put with initializer
    try:
        age = float(expInfo['age'])
    except ValueError:
        raise ValueError("Please enter age in years")

    # Set Run Number and Duration based on Age and Scan Type
    if expInfo['scan type'] == 'mbPCASL':
        nRuns = 1
        runDuration = 325.2  # sec
    else:  # expInfo['scan type'] == 'REST'
        if age >= 8:
            nRuns = 2
            runDuration = 390.4  # sec plus TR adjustmnet
        else:  #if 5-7yo
            nRuns = 3
            runDuration = 210.4  # .8ms TR * 263 Frames

    # Eye-Tracking Params
    recVideo = config['record'] == 'yes'
    useAperture = config['use_aperture'] == 'yes'

    if recVideo:
        # Only import opencv if using video so the script is runnable w/o eyetracking setup
        if useAperture:
            aperture = config['aperture']

        #Camera number (should be 1 for scanning if using computer w/ built-in camera (e.g., FaceTime on a Macbook);
        #use 0 if your computer does not have a built-in camera or if you are testing script w/ built-in camera:
        if expInfo['test mode']:
            eyeCam = 0
        else:
            if config['dualCam'] =='yes' or config['dualCam'] ==1:
                eyeCam = 1
            else:
                eyeCam = 0
    else:
        eyeCam, aperture = 0, None

    return expInfo, logFile, expName, nRuns, recVideo, eyeCam, useAperture, aperture, runDuration, filebase

def recFrame(cap, aperture=None):
    #read a frame from the cv device `cap`, queue it to write, and display it:
    ret, frame = cap.read()
    if aperture:
        update_queue.put(reFrame(frame, aperture))
        cv2.imshow('RA View', reFrame(frame, aperture))
    else:
        update_queue.put(frame)
        cv2.imshow('RA View', frame)


#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Main experiment:
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
if __name__ == "__main__":
    #User information
    expInfo, logFile, expName, nRuns, recVideo, eyeCam, useAperture, aperture, runDuration, filebase = scanInit()

    # Setup the participant Window
    # put inside name=main
    win = visual.Window(size=resolution, fullscr=False, screen=pScreen, allowGUI=False, allowStencil=False,
                        monitor=mon, color=[-1,-1,-1], colorSpace='rgb',
                        blendMode='avg', useFBO=True, units='deg')
    #Create fixation cross object:
    cross = visual.TextStim(win=win, ori=0, name='cross',
                            text='+',    font='Arial',
                            pos=[0, 0], height=fixLetterSize, wrapWidth=None,
                            color='white', colorSpace='rgb', opacity=1,
                            depth=-1.0)
    #Display fixation:
    fixCross(win, cross)
    #Display RA instructions:
    raWin = instruct(expInfo['scan type'])
    #Create other instructions:
    waitText = visual.TextStim(win=raWin, ori=0, name='introText',
        text='Waiting for trigger...', font='Arial',
        pos=[0, 0], height=titleLetterSize, wrapWidth=30,
        color='white', colorSpace='rgb', opacity=1,
        depth=-1.0)
    countText = visual.TextStim(win=raWin, ori=0, name='countText',
        text='Count down...', font='Arial',
        pos=[0, 0], height=titleLetterSize, wrapWidth=30,
        color='white', colorSpace='rgb', opacity=1,
        depth=-1.0)
    recText = visual.TextStim(win=raWin, ori=0, name='recText',
        text='Recording...', font='Arial',
        pos=[0, 0], height=titleLetterSize, wrapWidth=30,
        color='white', colorSpace='rgb', opacity=1,
        depth=-1.0)
    ioText = visual.TextStim(win=raWin, ori=0, name='ioText',
        text='Writing video...', font='Arial',
        pos=[0, 0], height=titleLetterSize, wrapWidth=30,
        color='white', colorSpace='rgb', opacity=1,
        depth=-1.0)
    norecText = visual.TextStim(win=raWin, ori=0, name='norecText',
        text='Scan in progress...', font='Arial',
        pos=[0, 0], height=titleLetterSize, wrapWidth=30,
        color='white', colorSpace='rgb', opacity=1,
        depth=-1.0)
    version = gitVersion()
    logging.exp('git-revision: %s' % version)
    runTS = []
    getOut = False
    globalClock = core.Clock()
    routineTimer = core.CountdownTimer()
    for thisRun in range(nRuns):
        events = []
        if recVideo:
            #Create video capture object to control camera/frame grabber:
            cap = cv2.VideoCapture(eyeCam)
            logging.debug('opened video reader on camera %u' % eyeCam)
            try:
                cap.set(cv2.cv.CV_CAP_PROP_FPS, value=vid_frame_rate)
            except StandardError:
                cap.set(cv2.CAP_PROP_FPS, value=vid_frame_rate)
            #Read a frame, get dims:
            ret, frame = cap.read()
            if useAperture:
                w = np.shape(reFrame(frame, aperture))[1]
                h = np.shape(reFrame(frame, aperture))[0]
            else:
                w = np.shape(frame)[1]
                h = np.shape(frame)[0]
        else:
            cap = None
        #Indicate script is waiting for trigger:
        waitText.draw()
        raWin.flip()
        
        # Run Output Filename
        filename = filebase + '_'.join(['', 'run%s' % (thisRun + 1), expInfo['date']])
    
        if recVideo:
            #Queue of frames from cap; data collection loop adds frames, video writing process
            #pops frames (FIFO):
            update_queue = Queue()
            #Flag to tell parallel process when to exit loop
            quit_flag = Value(c_bool, False)

            #Write file in another process:
            writeProc = Process(name='Write',
                                target=writeVid,
                                args=(update_queue, quit_flag, thisRun, filename + vidExt))
            writeProc.start()
            
            #Initialize the cv2 Window (so we can re-focus back to psychopy)
            cv2.namedWindow('RA View', cv2.WINDOW_AUTOSIZE)


        # Bring Participant Window to the front
        win.winHandle.activate()

        # Wait for scanner trigger; zero clocks at trigger time:
        trigger_ts, triggerWallTime = waitForTrigger([globalClock, routineTimer])

        # Start timing for the length of the scan
        routineTimer.add(runDuration)

        expInfo['triggerWallTime'] = triggerWallTime.strftime(timestampFormat)
        events.append({'condition': 'ScanStart',
                       'run': 'run%d' % (thisRun + 1),
                       'duration': 0,
                       'onset': globalClock.getTime()})

        #Capture a timestamp for every frame (1st entry will be trigger):
        runTS.append([])  # Start a new list for this run's timestamps
        if expInfo['scan type'] == 'REST':
            events.append({'condition': 'Countdown',
                           'run': 'run%d' % (thisRun + 1),
                           'duration': 8,
                           'onset': globalClock.getTime()})
            countText.draw(raWin)
            raWin.flip()
            count_down(win, cap=cap, aperture=aperture, timestamps=runTS[thisRun], clock=globalClock)
        events.append({'condition': 'FixStart',
                       'run': 'run%d' % (thisRun + 1),
                       'duration': 0,
                       'onset': globalClock.getTime()})

        fixCross(win, cross)
        if recVideo:
            #Data collection loop:
            recText.draw(raWin)
            raWin.flip()
        else:
            norecText.draw(raWin)
            raWin.flip()


        # Bring Participant Window to the front
        win.winHandle.activate()
        while routineTimer.getTime() > 0 and not endExpNow:
            #collect time stamp for each image:
            if event.getKeys(keyList=[quitKey]):
                scanOver = True
                if recVideo:
                    writeProc.terminate()
                    cap.release()
                    cv2.destroyAllWindows()
                core.quit()
                endExpNow = True
                break
            if recVideo:
                recFrame(cap, aperture=aperture)
                runTS[thisRun].append(globalClock.getTime())
        runEndTime = datetime.datetime.today()
        logging.info('Run %s finished: %s' % (thisRun + 1, runEndTime.strftime(timestampFormat)))
        events.append({'condition': 'RunEnd',
                       'duration': 0,
                       'run': 'run%d' % (thisRun + 1),
                       'onset': globalClock.getTime()})
        run_df = pd.DataFrame(events)
        run_df.to_csv(filename + '_design.csv')
        run_df['git-revision'] = version
        if recVideo:
            ioText.draw(raWin)
            raWin.flip()
            raWin.winHandle.activate()
            #Flip quit_flag to True when done:
            quit_flag.value = True
            #End writing proca:
            writeProc.terminate()
            #Get some timing stats, print some, save the rest to .csv:
            timing = pd.DataFrame({'TS': runTS[thisRun]})
            timing['second'] = np.floor(timing['TS'])
            x = timing.groupby('second')['second'].count()
            print('**********************************************************')
            print('**********************************************************')
            print('**********************************************************')
            print('Run ' + str(thisRun + 1) + ' Timing Diagnostics:')
            print('**********************************************************')
            print('Frequency: Frames Within Each Second')
            out_dist = x.groupby(x).count()
            print(out_dist)
            out_dist.to_csv(filebase + 'EyeCamFPS_Dist.csv')
            print('**********************************************************')
            #Save timestamps:
            cap.release()
            cv2.destroyAllWindows()

            #Time stamp file name:
            out_file_ts = filename + '_ts.csv'
            #Save timestamp file:
            np.savetxt(out_file_ts, runTS[thisRun], delimiter=',', fmt='%.04f')

    # Log Settings
    # put inside name=main
    logging.info(expInfo)
    logging.info('nRuns: %d, runDuration: %.02f' % (nRuns, runDuration))
    logging.info('Recording frame rate: %d' % vid_frame_rate)

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #Clean up & shut  down
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    win.close()
    raWin.close()
    print('Script Finished!')
    core.quit()
