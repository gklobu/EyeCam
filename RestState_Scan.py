"""

***************************************************************************************************************
This experiment was created using PsychoPy2 Experiment Builder (v1.83.04), Thu Dec  8 16:36:30 2016
If you publish work using this script please cite the relevant PsychoPy publications
  Peirce, JW (2007) PsychoPy - Psychophysics software in Python. Journal of Neuroscience Methods, 162(1-2), 8-13.
  Peirce, JW (2009) Generating stimuli for neuroscience using PsychoPy. Frontiers in Neuroinformatics, 2:10. doi: 10.3389/neuro.11.010.2008
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
Gian Klobusicky
gklobusicky@fas.harvard.edu
01/31/2017
"""

from multiprocessing import Process, Queue, Value
from ctypes import c_bool
from psychopy import locale_setup, visual, core, data, event, logging, sound, gui
import pyglet
import cv2
import numpy as np
import pandas as pd
import os
import sys
import datetime

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#User input
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
expInfo = {'scan type':['SELECT SCAN TYPE', 'REST', 'ASL'], 'age': u'', u'participant': u'', 'session':u'', 'test mode':False}
dlg = gui.DlgFromDict(dictionary=expInfo, title='Eye Cam')
if dlg.OK == False: core.quit()  # user pressed cancel
expInfo['date'] = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')  # add a simple timestamp
if expInfo['scan type']=='SELECT SCAN TYPE':
    raise ValueError('CHOOSE A SCAN TYPE!!!')
else:
    expName = expInfo['scan type']

expInfo['expName'] = expName
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Params
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# Ensure that relative paths start from the same directory as this script
_thisDir = os.path.dirname(os.path.abspath(__file__)).decode(sys.getfilesystemencoding())
os.chdir(_thisDir)
#Participant's screen (for fixation cross; should be 1, indicating an external monitor, while scanning; may use 0 to test script without external monitor):
pScreen = 1
#RA's screen (for eye video monitor; should usually be 0):
raScreen = 0
#Monitor calibration (for participant's screen):
pMon = "testMonitor"
#Frame rate (for recording):
rec_frame_rate = 30
#Number of seconds in a run:
runTime = 401 if expName=='REST' else 240
#Key that ends experiment:
quitKey = 'escape'

# Data file name stem = absolute path + name; later add .psyexp, .csv, .log, etc
filename = _thisDir + os.sep + u'data/%s_%s_%s_%s' %(expName, expInfo['participant'],
            expInfo['session'], expInfo['date'])
print(filename)
#Video encoding:
vidExt = '.mp4'
#Time stamp file name:
out_file_ts = filename + '_ts.csv'

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Basic experiment setup
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# An ExperimentHandler isn't essential but helps with data saving
thisExp = data.ExperimentHandler(name=expName, version='',
    extraInfo=expInfo, runtimeInfo=None,
    originPath=None,
    savePickle=True, saveWideText=True,
    dataFileName=filename)
#save a log file for detail verbose info
logFile = logging.LogFile(filename+'.log', level=logging.EXP)
logging.console.setLevel(logging.WARNING)  # this outputs to the screen, not a file
#Create display:
display = pyglet.window.get_platform().get_default_display()
screens = display.get_screens()
#dims for participant screen (ra screen set below):
pwidth = screens[pScreen].width
pheight = screens[pScreen].height

endExpNow = False  # flag for 'escape' or other condition => quit the exp

# Initialize components for Routine "intro"
introClock = core.Clock()
import yaml
import itertools

if os.path.exists('siteConfig.yaml'):
    with open('siteConfig.yaml') as f:
        config = yaml.safe_load(f)
else:
    copyMsg = ('Please copy configuration text file '
               '"siteConfig.yaml.example" to "siteConfig.yaml" '
               'and edit it with your trigger and buttons.')
    raise IOError(copyMsg)

try:
    age = float(expInfo['age'])
except ValueError:
    raise ValueError("Please enter age in years")

if age >=8 and age <= 80:
    nRuns=2
else: #if 5-7yo or 81+ yo
    nRuns=3

triggerKey = config['trigger'] #5 at Harvard
titleLetterSize = config['style']['titleLetterSize']  # 3
textLetterSize = config['style']['textLetterSize']  # 1.5
fixLetterSize = config['style']['fixLetterSize']  # 2.5
wrapWidth = config['style']['wrapWidth']  # 30
subtitleLetterSize = config['style']['subtitleLetterSize']  # 1
recVideo = config['record']=='yes'
useAperture = config['use_aperture'] == 'yes'
if recVideo and useAperture:
    aperture = config['aperture']
#Camera number (should be 1 for scanning if using computer w/ built-in camera (e.g., FaceTime on a Macbook);
#use 0 if your computer does not have a built-in camera or if you are testing script w/ built-in camera:
eye_cam = 1 if config['dualCam'] and not expInfo['test mode'] else 0

def instruct():
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
    raText= visual.TextStim(win=raWin, ori=0, name='raText',
        text='', font='Arial',
        pos=[0, 0], height=textLetterSize*.8, wrapWidth=30,
        color='white', colorSpace='rgb', opacity=1,
        depth=0.0)
    outerFrame = visual.Rect(win=raWin, lineWidth=1, lineColor='white',
                             width=35, height=23, units='deg')
    #Update RA text (i.e., instructions):
    raText.text='"In the next scan all you are going to see is a white plus sign in the middle of the screen. Your job is to simply rest, keep your eyes open, and look at the plus sign during the entire scan. You can blink normally, and you do not have to think about anything in particular. However, it is very important that you do not fall asleep, and as always, that you stay very still from beginning to end. \n\nDoes that make sense? Do you have any questions? Are you ready to begin?" \n\nPress <space> to continue.'
    raText.draw()
    raWin.flip()
    raWin.winHandle.activate()
    loopOver = False
    while not loopOver:
        inkeys = event.getKeys()
        if quitKey in inkeys:
            endExpNow = True
            core.quit()
            loopOver = True
        elif 'space' in inkeys:
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
def fixCross():
    # Setup the Window
    win = visual.Window(size=(pwidth, pheight), fullscr=False, screen=pScreen, allowGUI=False, allowStencil=False,
    monitor='testMonitor', color=[-1,-1,-1], colorSpace='rgb',
    blendMode='avg', useFBO=True,
    units='deg')
    cross = visual.TextStim(win=win, ori=0, name='cross',
    text='+',    font='Arial',
    pos=[0, 0], height=fixLetterSize, wrapWidth=None,
    color='white', colorSpace='rgb', opacity=1,
    depth=-1.0)
    cross.draw(win)
    win.mouseVisible = False
    win.flip()
    return win
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Wait for scanner trigger
#Returns trigger timestamp
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def waitForTrigger():
    trigger_ts = core.getTime()
    loopOver = False
    while not loopOver:
        inkeys = event.getKeys()
        if triggerKey in inkeys:
            trigger_ts = core.getTime() #time stamp for start of scan
            loopOver = True
        elif quitKey in inkeys:
            endExpNow = True
            core.quit()
            loopOver = True
    print('Trigger received!!!')
    return trigger_ts
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Video writing function
#To be run in parallel with data collection loop in main
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def writeVid(update_queue, quit_flag, thisRun):
    #CV2 does not like to run in two processes simultaneously:
    import imageio
    #Create video writer object:
    out_file = filename + "_run" + str(thisRun+1) + vidExt
    out = imageio.get_writer(out_file, fps=rec_frame_rate)
    while not quit_flag.value:
        #Keep popping and writing frames:
        out.append_data(update_queue.get())
    #Finishes file IO when quit_flag is flipped to True:
    out.close()

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Main experiment:
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
if __name__ == "__main__":
    #Display fixation:
    win = fixCross()
    #Display RA instructions:
    raWin = instruct()
    #Create other instructions:
    waitText = visual.TextStim(win=raWin, ori=0, name='introText',
        text='Waiting for trigger...', font='Arial',
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
    runTS = [[],[]]
    getOut = False
    for thisRun in range(nRuns):
        if recVideo:
            #Create video capture object to control camera/frame grabber:
            cap = cv2.VideoCapture(eye_cam)
            cap.set(cv2.cv.CV_CAP_PROP_FPS, value=rec_frame_rate)
            #Read a frame, get dims:
            ret, frame = cap.read()
            if useAperture:
                w=np.shape(reFrame(frame, aperture))[1]
                h=np.shape(reFrame(frame, aperture))[0]
            else:
                w=np.shape(frame)[1]
                h=np.shape(frame)[0]
        #Indicate script is waiting for trigger:
        waitText.draw(raWin)
        raWin.flip()
        raWin.winHandle.activate()
        #Wait for scanner trigger:
        trigger_ts = waitForTrigger()
        #Capture a timestamp for every frame (1st entry will be trigger):
        runTS[thisRun]+=[trigger_ts]
        if recVideo:
            #Queue of frames from cap; data collection loop adds frames, video writing process
            #pops frames (FIFO):
            update_queue = Queue()
            #Flag to tell parallel process when to exit loop
            quit_flag = Value(c_bool, False)
            #Write file in another process:
            writeProc = Process(name='Write', target=writeVid, args=(update_queue, quit_flag, thisRun))
            writeProc.start()
            #Data collection loop:
            recText.draw(raWin)
            raWin.flip()
            raWin.winHandle.activate()
        else:
            norecText.draw(raWin)
            raWin.flip()
            raWin.winHandle.activate()
        scanOver = False
        while not scanOver and not endExpNow:
            #Check to see if scan is over:
            scanOver = (runTS[thisRun][-1]-trigger_ts)>runTime
            #collect time stamp for each image:
            runTS[thisRun]+=[core.getTime()]
            if event.getKeys(quitKey):
                scanOver = True
                writeProc.terminate()
                cap.release()
                core.quit()
                cv2.destroyAllWindows()
                endExpNow = True
                break
            if recVideo:
                #read a frame, queue it, and display it:
                ret, frame = cap.read()
                if useAperture:
                    update_queue.put(reFrame(frame, aperture))
                    cv2.imshow('RA View', reFrame(frame, aperture))
                else:
                    update_queue.put(frame)
                    cv2.imshow('RA View', frame)
        if recVideo:
            ioText.draw(raWin)
            raWin.flip()
            raWin.winHandle.activate()
            #Flip quit_flag to True when done:
            quit_flag.value = True
            #End writing proca:
            writeProc.terminate()
            #Get some timing stats, print some, save the rest to .csv:
            timing = pd.DataFrame({'TS':runTS[thisRun]})
            timing['second'] = np.floor(timing['TS'])
            x = timing.groupby('second')['second'].count()
            print('**********************************************************')
            print('**********************************************************')
            print('**********************************************************')
            print('Run ' + str(thisRun+1) + ' Timing Diagnostics:')
            print('**********************************************************')
            print('Frequency: Frames Within Each Second')
            print(x.groupby(x).count())
            print('**********************************************************')
            #Save timestamps:
            cap.release()
            cv2.destroyAllWindows()
    if recVideo:
        #Save timestamp file:
        np.savetxt(out_file_ts, runTS[0]+runTS[1], delimiter=',')
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #Clean up & shut  down
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    win.close()
    raWin.close()
    core.quit()
    print('Script Finished!')
