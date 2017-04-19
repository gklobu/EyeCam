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
import cv2  # try to import with others


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
    raWin = visual.Window(size=[1100, 675], fullscr=False, allowGUI=True, allowStencil=False,
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
                                   pos=[0, 3], height=1.5, wrapWidth=30,
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
    loopOver = False
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
#Countdown 4,3,2,1 every 2 seconds at start of REST
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def count_down(win, recorder, record_countdown=False):
    # Create images for Routine "countdown"
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
        while core.getTime() - flip_time < 2:
            if record_countdown:
                recorder.cap_frame(globalClock)
            if event.getKeys(quitKey):
                if recorder:
                    recorder.close()
                core.quit()
                break


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
            runDuration = 180

    # Eye-Tracking Params
    recVideo = config['record'] == 'yes'
    useAperture = config['use_aperture'] == 'yes'

    if recVideo:
        #Camera number (should be 1 for scanning if using computer w/ built-in camera (e.g., FaceTime on a Macbook);
        #use 0 if your computer does not have a built-in camera or if you are testing script w/ built-in camera:
        if expInfo['test mode']:
            eyeCam = 0
        else:
            if config['dualCam'] =='yes' or config['dualCam'] ==1:
                eyeCam = 1
            else:
                eyeCam = 0

        # Initialize a recorder to handle frame grabber and timestamps
        recorder = Recorder(eyeCam)
        if useAperture:
            recorder.aperture = config['aperture']
    else:
        recorder = None

    if 'record_countdown' in config.keys():
        record_countdown = config['record_countdown'] == 'yes'
    else:
        record_countdown = False

    return expInfo, logFile, expName, nRuns, recorder, runDuration, filebase, record_countdown


class Recorder(object):
    '''The Recorder maintains state for recording from the EyeCam, including the opencv framegrabber (cap)
       and the `multiprocessing` Queue and writing process, as well as deleter functions to cleanly close
       everything up.
       
       Initialization:
        
        * eyeCam (int): Camera to use for tracking (0-indexed, according to available cameras on the system).
        
       Usage:
        * Call open_cap() and start_queue() to open a framegrabber and close() to end.
        
       Attributes:
        * cap (opencv.VideoCapture): Opencv framegrabber (opened on initialization)
        * timestamps (list): List of timestamps tied to video frames
        * vid_frame_rate (int): Target frame rate to acquire video
        * update_queue (multiprocessing.Queue): Queue to use for asynchronous writing of movie frames
        * writeProc (multiprocessing.Process): Function to use for asynchronous writing of movie frames
       '''
    def __init__(self, eyeCam=0, aperture=None, vid_frame_rate=30):
        self.eyeCam = eyeCam
        self.aperture = aperture
        self.vid_frame_rate = vid_frame_rate
        self.update_queue = None
        self.timestamps = []
        self._cap = None

    @property
    def cap(self):
        return self._cap

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #Create opencv framegrabber
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def open_cap(self):
        # Create video capture object to control camera/frame grabber:
        cap = cv2.VideoCapture(self.eyeCam)
        self._cap = cap
        logging.debug('opened video reader on camera %u' % self.eyeCam)
        try:
            cap.set(cv2.cv.CV_CAP_PROP_FPS, value=vid_frame_rate)
        except StandardError:
            cap.set(cv2.CAP_PROP_FPS, value=self.vid_frame_rate)
        # Read a frame, get dims:
        ret, frame = cap.read()
        if self.aperture:
            w = np.shape(reFrame(frame, self.aperture))[1]
            h = np.shape(reFrame(frame, self.aperture))[0]
        else:
            w = np.shape(frame)[1]
            h = np.shape(frame)[0]
        self.w = w
        self.h = h

    @cap.deleter
    def cap(self):
        self._cap.release()
        del(self._cap)
        cv2.destroyAllWindows()

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #Open frame grabber queue and writing process
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def start_queue(self, out_file):
        # Queue of frames from cap; data collection loop adds frames, video writing process
        # pops frames (FIFO):
        if not self.update_queue:
            self.update_queue = Queue()

        # Flag to tell parallel process when to exit loop
        self.quit_flag = Value(c_bool, False)

        # Write file in another process:
        self.writeProc = Process(name='Write',
                                 target=self.writeVid,
                                 args=(out_file,))
        self.writeProc.start()

        # Initialize the cv2 Window (so we can re-focus back to psychopy)
        cv2.namedWindow('RA View', cv2.WINDOW_AUTOSIZE)

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #Capture a single frame, and record image and timestamp
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def cap_frame(self, clock):
        # read a frame, queue it, and display it:
        ret, _frame = self._cap.read()
        self.timestamps.append(clock.getTime())
        if self.aperture:
            frame = reFrame(_frame, self.aperture)
        else:
            frame = _frame

        self.update_queue.put(frame)
        cv2.imshow('RA View', frame)

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #Video writing function
    #To be run in parallel with data collection loop in main
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def writeVid(self, out_file):
        # CV2 does not like to run in two processes simultaneously:
        import imageio
        # Create video writer object:
        out = imageio.get_writer(out_file, fps=self.vid_frame_rate)
        while not self.quit_flag.value:
            # Keep popping and writing frames:
            out.append_data(self.update_queue.get())
        # Finishes file IO when quit_flag is flipped to True:
        out.close()

    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #Cleanup Everything in recorder
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    def close(self):
        '''Close everything, including the multiprocessing queue, frame writer, and opencv framegrabber'''
        self.quit_flag = True
        del(self.cap)
        self.update_queue.close()
        del(self.update_queue)
        self.update_queue = None
        self.writeProc.terminate()


def write_ts_hist(ts_arr, out_file, thisRun):
    '''Calculate, display and save histogram of timestamps'''
    timing = pd.DataFrame({'TS': ts_arr})
    timing['second'] = np.floor(timing['TS'])
    x = timing.groupby('second')['second'].count()
    out_dist = x.groupby(x).count()
    print('**********************************************************')
    print('**********************************************************')
    print('**********************************************************')
    print('Run ' + str(thisRun + 1) + ' Timing Diagnostics:')
    print('**********************************************************')
    print('Frequency: Frames Within Each Second')
    print(out_dist)
    print('**********************************************************')
    out_dist.to_csv(out_file)

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Main experiment:
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
if __name__ == "__main__":
    #User information
    expInfo, logFile, expName, nRuns, recorder, runDuration, filebase, record_countdown = scanInit()

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
    version = gitVersion()
    logging.exp('git-revision: %s' % version)
    getOut = False
    globalClock = core.Clock()
    routineTimer = core.CountdownTimer()
    for thisRun in range(nRuns):
        # Initialize logs for thisRun
        events = []
        filename = filebase + '_'.join(['', 'run%s' % (thisRun + 1), expInfo['date']])


        # Open Video Capture
        if recorder:
            vid_out = out_file = filename + vidExt
            recorder.open_cap()
            recorder.start_queue(vid_out)
            recorder.timestamps = []  # Init a new list of timestamps for this run

        # Indicate script is waiting for trigger:
        waitText.draw()
        raWin.flip()
        raWin.winHandle.activate()

        # Wait for scanner trigger; zero clocks at trigger time:
        trigger_ts, triggerWallTime = waitForTrigger([globalClock, routineTimer])

        # Start timing for the length of the scan
        routineTimer.add(runDuration)

        win.winHandle.activate()
        raWin.winHandle.activate()

        expInfo['triggerWallTime'] = triggerWallTime.strftime(timestampFormat)
        events.append({'condition': 'ScanStart',
                       'run': 'run%d' % (thisRun + 1),
                       'duration': 0,
                       'onset': globalClock.getTime()})

        if expInfo['scan type'] == 'REST':
            events.append({'condition': 'Countdown',
                           'run': 'run%d' % (thisRun + 1),
                           'duration': 8,
                           'onset': globalClock.getTime()})
            countText.draw(raWin)
            raWin.flip()
            win.mouseVisible = False
            count_down(win, recorder, record_countdown)

        events.append({'condition': 'FixStart',
                       'run': 'run%d' % (thisRun + 1),
                       'duration': 0,
                       'onset': globalClock.getTime()})

        # Draw Fixation cross on participant screen
        fixCross(win, cross)
        if recorder:
            msg = 'Recording...'
        else:
            msg = 'Scan in progress...'
        recText.text = msg
        recText.draw(raWin)
        raWin.flip()

        while routineTimer.getTime() > 0 and not endExpNow:
            if event.getKeys(quitKey):
                scanOver = True
                endExpNow = True
                if recorder:
                    recorder.close()
                break
            if recorder:
                # Record a frame and timestamp
                recorder.cap_frame(globalClock)
        runEndTime = datetime.datetime.today()
        logging.info('Run %s finished: %s' % (thisRun + 1, runEndTime.strftime(timestampFormat)))
        events.append({'condition': 'RunEnd',
                       'duration': 0,
                       'run': 'run%d' % (thisRun + 1),
                       'onset': globalClock.getTime()})
        run_df = pd.DataFrame(events)
        run_df.to_csv(filename + '_design.csv')
        run_df['git-revision'] = version
        if recorder:
            ioText.draw(raWin)
            raWin.flip()
            raWin.winHandle.activate()
            # Flip quit_flag to True when done:
            recorder.close()

            # Get some timing stats, print some, save the rest to .csv:
            write_ts_hist(recorder.timestamps,
                          filename + '_EyeCamFPS_Dist.csv',
                          thisRun)

            #Time stamp file name:
            out_file_ts = filename + '_ts.csv'
            #Save timestamp file:
            np.savetxt(out_file_ts, recorder.timestamps, delimiter=',', fmt='%.04f')

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
