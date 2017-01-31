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
import os
import sys
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
#Camera number (because some laptops have built-in cameras):
eye_cam = 1
#Frame rate (for recording):
rec_frame_rate = 30
#Number of pixels by which to translate camera aperture:
shift = 5

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Read params
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
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
titleLetterSize = config['style']['titleLetterSize']  # 3
textLetterSize = config['style']['textLetterSize']  # 1.5
wrapWidth = config['style']['wrapWidth']  # 30
subtitleLetterSize = config['style']['subtitleLetterSize']  # 1
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#Image cropping function
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::
def reFrame(fr, aperture):
    return fr[aperture[0]:aperture[1], aperture[2]:aperture[3], :]
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
    #default aperture is 20% of screen (centered)
    aperture = [int(o_frame_dim[0]//2 - o_frame_dim[0]*0.10),
                int(o_frame_dim[0]//2 + o_frame_dim[0]*0.10),
                int(o_frame_dim[1]//2 - o_frame_dim[1]*0.10),
                int(o_frame_dim[1]//2 + o_frame_dim[1]*0.10)]
    #key dict to move & resize aperture (by pixels):
    ap_map = {"up":[-shift,-shift,0,0],
                "down": [shift,shift,0,0],
                "left": [0,0,-shift,-shift],
                "right":[0,0,shift,shift],
                "b":[-1,1,-1,1], #bigger
                "s":[1,-1,1,-1]} #smaller
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
        key = event.getKeys(ap_map.keys()+["q"])
        if len(key)==1:
            if key[0]=="q":
                done=True
            else:
                newapp = [aperture[i]+ap_map[key[0]][i] for i in range(len(aperture))]
                aperture = newapp if checkAp(newapp) else aperture
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
    with open('siteConfig.yaml', 'w') as f:
        config = yaml.dump(config, f)
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #Clean up & shut  down
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    raWin.close()
    core.quit()
    print('Finished!')