"""
***************************************************************************************************************
This experiment was created using PsychoPy2 Experiment Builder (v1.83.04), Thu Dec  8 16:36:30 2016
If you publish work using this script please cite the relevant PsychoPy publications
  Peirce, JW (2007) PsychoPy - Psychophysics software in Python. Journal of Neuroscience Methods, 162(1-2), 8-13.
  Peirce, JW (2009) Generating stimuli for neuroscience using PsychoPy. Frontiers in Neuroinformatics, 2:10. doi: 10.3389/neuro.11.010.2008
***************************************************************************************************************
Script to calibrate aperture of frame grabber for resting state script
Displays real-time Eyelink video for RA on main monitor

Gian Klobusicky
gklobusicky@fas.harvard.edu
01/14/2017
"""

from psychopy import core, visual, event, gui
import cv2
import numpy as np
import math
import os
import sys
import yaml
import itertools


#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Params
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::

# Ensure that relative paths start from the same directory as this script
_thisDir = os.path.dirname(os.path.abspath(__file__)).decode(sys.getfilesystemencoding())
os.chdir(_thisDir)
#RA's screen (for eye video):
raScreen = 0
#Monitor calibration (for participant's screen):
pMon = 'testMonitor'
#Frame rate (for recording):
rec_frame_rate = 30
#Number of pixels by which to translate camera aperture:
SHIFT_COEFF = 30
#Number of pixels (on each side) by which to grow or shrink camera aperture:
SCALE_COEFF = 15
#aperture transformations:
AP_MAP = {"up":[-1,-1,0,0],
                "down": [1,1,0,0],
                "left": [0,0,-1,-1],
                "right":[0,0,1,1],
                "b":[-1,1,-1,1], #bigger
                "s":[1,-1,1,-1]} #smaller
#Location of configuration file:
CONFIG_FILE = 'siteConfig.yaml'

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Read params
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#load configuration file
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE) as f:
        config = yaml.safe_load(f)
else:
    copyMsg = ('Please copy configuration text file '
               '"siteConfig.yaml.example" to "siteConfig.yaml" '
               'and edit it with your trigger and buttons.')
    raise IOError(copyMsg)
titleLetterSize = config['style']['titleLetterSize']  # 3
textLetterSize = config['style']['textLetterSize']  # 1.5
wrapWidth = config['style']['wrapWidth']  # 30
subtitleLetterSize = config['style']['subtitleLetterSize']  # 1
#Camera number (because some laptops have built-in cameras):
if config['dualCam'] == 'yes' or config['dualCam'] == 1:
    eye_cam = 1
else:
    eye_cam = 0
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Image cropping function
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def reFrame(fr, aperture):
    return fr[aperture[0]:aperture[1], aperture[2]:aperture[3], :]

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Aperture fixing function
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def closestLegalAperture(aperture, vidSize):
    ''' return the closest aperture which is of even width and height and fully within vidSize.
    aperture format is [top bottom left right], vidSize format is [height width]'''
    
    def ap2size(ap):
        size = [ap[1] - ap[0], ap[3] - ap[2]]
        return size
    apSize = ap2size(aperture)

    #if height and/or width are odd, expand them by one pixel to make them even
    if apSize[0] % 2 != 0:
        aperture[1] += 1
        apSize = ap2size(aperture)
    if apSize[1] % 2 != 0:
        aperture[3] += 1
        apSize = ap2size(aperture)
        
    #if aperture is larger than vidSize, shrink it to the closest even size that fits
    if apSize[0] > vidSize[0]:
        amntOver = apSize[0] - vidSize[0]
        print('aperture: ')
        print(aperture)
        print('over by %u' % amntOver)
        shrinkCoeff = amntOver / 2 + amntOver % 2 #if vidSize is odd for some reason, this should handle it
        aperture = [aperture[i] + shrinkCoeff * AP_MAP['s'][i] for i in range(len(aperture))] 
        apSize = ap2size(aperture)
        print(aperture)
    if apSize[1] > vidSize[1]:
        amntOver = apSize[1] - vidSize[1]
        shrinkCoeff = amntOver / 2. + amntOver % 2
        aperture = [aperture[i] + shrinkCoeff * AP_MAP['s'][i] for i in range(len(aperture))]
        apSize = ap2size(aperture)

    #if the aperture extends off the screen, bring it back on
    if aperture[0] < 0: #top
        #aperture = np.add(aperture, np.multiply(-aperture[0], AP_MAP['down']))
        aperture = [aperture[i] - (aperture[0] * AP_MAP['down'][i]) for i in range(len(aperture))]
    if aperture[2] < 0: #left
        aperture = [aperture[i] - aperture[2] * AP_MAP['right'][i] for i in range(len(aperture))]
    if aperture[1] > vidSize[0] : #bottom
        aperture = [aperture[i] + (aperture[1]-vidSize[0]) * AP_MAP['up'][i] for i in range(len(aperture))]
    if aperture[3] > vidSize[1] : #right
        aperture = [aperture[i] + (aperture[3]-vidSize[1]) * AP_MAP['left'][i] for i in range(len(aperture))]

    #print(aperture)
    return aperture 

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Aperture calibration function
#Returns aperture
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def calibrate():
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #Psychopy setup & display
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #Create vid capture object:
    cap = cv2.VideoCapture(eye_cam) 
    #Read a frame:
    ret, frame = cap.read()
    
    #x, y dimensions of the frame:
    o_frame_dim = np.shape(np.array(frame))
    print(np.shape(frame))
    #if an aperture was already in siteConfig, use it
    if 'aperture' in config:
        aperture = closestLegalAperture(config['aperture'], o_frame_dim)
    else:
        #default aperture is 20% of screen (centered)
        aperture = [int(o_frame_dim[0]//2 - o_frame_dim[0]*0.10),
                    int(o_frame_dim[0]//2 + o_frame_dim[0]*0.10),
                    int(o_frame_dim[1]//2 - o_frame_dim[1]*0.10),
                    int(o_frame_dim[1]//2 + o_frame_dim[1]*0.10)]
    #key dict to move & resize aperture (by pixels):
    ap_map = {"up":[-SHIFT_COEFF,-SHIFT_COEFF,0,0],
                "down": [SHIFT_COEFF,SHIFT_COEFF,0,0],
                "left": [0,0,-SHIFT_COEFF,-SHIFT_COEFF],
                "right":[0,0,SHIFT_COEFF,SHIFT_COEFF],
                "b":[-SCALE_COEFF,SCALE_COEFF,-SCALE_COEFF,SCALE_COEFF], #bigger
                "s":[SCALE_COEFF,-SCALE_COEFF,SCALE_COEFF,-SCALE_COEFF]} #smaller
    #To make sure aperture stays within the screen's limits
    def checkAp(ap):
        return np.all([i>0 for i in ap]) and ap[1]<=o_frame_dim[0] and ap[3]<=o_frame_dim[1]
    #Adjust the frame/aperture:
    done = False
    while not done:
        #Get new image:
        ret, frame = cap.read()
        frame = reFrame(frame, aperture)
        #Display the frame if it exists:
        if ret:
            cv2.imshow("Aperture", frame)
        #Check for keypress:
        key = event.getKeys(AP_MAP.keys()+["q"])
        if len(key)==1:
            if key[0]=="q":
                done=True
            else:
                newapp = [aperture[i]+ap_map[key[0]][i] for i in range(len(aperture))]
                aperture = closestLegalAperture(newapp, o_frame_dim)
    #Shut down cv2 objects:
    cap.release()
    cv2.destroyAllWindows()
    return aperture

if __name__ == "__main__":
    # Setup the RA Experimenter Window
    raWin = visual.Window(size=[600,500], fullscr=False, allowGUI=True, allowStencil=False,
        monitor=u'testMonitor', color=u'black', colorSpace='rgb',
        blendMode='avg', useFBO=True,
        units='deg',
        screen=raScreen)
    instructText = visual.TextStim(win=raWin, ori=0, name='introText',
        text='Arrow keys will move the aperture\n\nb: Bigger aperture\ns:Smaller aperture\n\nq:Finished', 
        font='Arial',
        pos=[0, 0], height=titleLetterSize//2, wrapWidth=30,
        color='white', colorSpace='rgb', opacity=1,
        depth=-1.0)
    instructText.draw(raWin)
    raWin.flip()
    raWin.winHandle.activate()

    #Allow user to crop the image:
    config['aperture'] = calibrate()
    print('Aperture:')
    print(config['aperture'])
    with open(CONFIG_FILE, 'w') as f:
        config = yaml.dump(config, f)
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #Clean up & shut  down
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    raWin.close()
    core.quit()
    print('Finished!')