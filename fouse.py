#!/usr/bin/env python

###########################################
# PW 2012/12/07: With these parameters, the stimuli will run for 3m54s (234s/117tr)
disable_motion   = True
test_seq         = False
## experiment vars
fixation_dur     = .500
target_dur       = .250
trial_dur        = .750
tr               = 2
# instruction time should be a multiple of tr!
instruction_time = 2
num_trials       = 32
block_len        = num_trials * trial_dur + instruction_time
num_blocks       = 9
num_1back        = 4
num_1back_cfound = 4
stim_scaler      = 2
validResponses   = ['1', '2', '3', '4']
motion_vectors   = [45, 135, -45, -135]
trigger_char	 = '+'
###########################################


## Standard Include Stanza
import VisionEgg

## load a visionegg config file, so we don't have to wait for the gui screen
#VisionEgg.config.VISIONEGG_CONFIG_FILE = './VisionEgg.cfg'

VisionEgg.start_default_logging();
VisionEgg.watch_exceptions()

from VisionEgg.Core import *
from VisionEgg.FlowControl import Presentation
from VisionEgg.Textures import *
from VisionEgg.MoreStimuli import *
from VisionEgg.Text import *

# PW 2012/11/26: To Blend images together
from PIL import Image

import pygame.image
import OpenGL.GL as gl

# PW 2012/11/26
#import Numeric
#from Numeric import *
import numpy
from numpy import *
import random

import sys
import getopt

import csv
import time
import optparse
from optparse import OptionParser
import fsbos_functions
from fsbos_functions import *


# Functions for experimental presentation
def oneTrial(t):
	  global loadStims, sitmulus
	  #t2 = t % trial_dur
	  #exp_item = exp_plan[int(floor(t/trial_dur))]
	  
          # PW: So this is ugly.  If you're reading this, my appologies.
          
          # Compute the block we are currently on
          current_block = floor(t/block_len)

          # What is the first index into exp_plan for this block?
          block_offset = int(floor(current_block*num_trials))

          # What time is it, relative to the time the first image is shown of this block?
	  block_time_idx = t - current_block*block_len - instruction_time         
          
          # If this index is negative, then show the instructions
          if block_time_idx < 0:
                block_time_idx = 0
		show_instructions = True
	  else:
		show_instructions = False

          # Compute the index into the 'plan'
          exp_idx = int(floor(block_offset + block_time_idx/trial_dur))

          # Extract the current row
	  exp_item = exp_plan[exp_idx]

	  t2 = block_time_idx % trial_dur

	  image_file = exp_item[3]		  	          
	  image_confound = exp_item[8]
	  alpha = exp_item[9]
          txt_instructions = exp_item[10]

          # Instructions should be taken from the block offset (not from exp_idx because
          # this will give the instructions from the *preivious* block)
	  #txt_instructions = (exp_plan[block_offset])[10]

          #Debug
	  #print "cb=%2.3f bo=%2.3f bti=%2.3f expi=%2.3f t2=%2.3f ei=%2d inst=%s" % (current_block, block_offset, block_time_idx, exp_idx, t2, exp_idx, txt_instructions)
          #print "t / total = %2.3f / %2.3f  img: %s  conf: %s" % (t, num_blocks * block_len, image_file, image_confound) 

	  if (show_instructions):
		if txt_instructions=='F':
			p.parameters.viewports = [ attend_face ]
		elif txt_instructions=='S':
			p.parameters.viewports = [ attend_scene ]
                else:
			p.parameters.viewports = [ viewport_fixation ]
		
	  else:
		  if t2 <= fixation_dur:
		      p.parameters.viewports = [ viewport_fixation ]
		      if loadStims == 0:

			  if image_file == 'fixation':
			      viewport_stimuli.parameters.stimuli = [ fixation ]
			  else:
			      try:
				  # PW 2012/11/26: Load with the PIL in order to blend them
			          #surface = pygame.image.load(image_file)
				  surface = Image.open(image_file).convert("RGB")
				  confound = Image.open(image_confound).convert("RGB").resize(surface.size)
			      except:
			          print "couldn't load image file: " + image_file
			          sys.exit(2)
			      #stimulus_texture = Texture(surface)
			      stimulus_texture = Texture(Image.blend(surface, confound, alpha))
			      stimulus.parameters.texture = stimulus_texture
			      viewport_stimuli.parameters.stimuli = [ stimulus ]
			  loadStims = 1
		  elif t2 > fixation_dur and t2 <= fixation_dur + target_dur:
		      p.parameters.viewports = [ viewport_stimuli ] 
		      loadStims = 0
		  elif t2 > fixation_dur + target_dur:
		      p.parameters.viewports = [ viewport_fixation ]

def keydown(event):
    if event.key == pygame.locals.K_ESCAPE:
        quit()
    elif (event.unicode in validResponses) == 1:
        data_writer.writerow([time.time() - exp_start_time, event.unicode])

def quit(dummy_arg=None):
    p.parameters.go_duration = (0, 'frames')
    sys.exit()

def waitForTrigger(event):
    if event.unicode == trigger_char:
      p1.parameters.go_duration = (0, 'seconds')      
    if event.key == pygame.locals.K_ESCAPE:
      quit()

def displayTime(t):
	cur_time.parameters.text = str(floor(t*100)/100)

global screen

# new way of processing command line variables
parser = OptionParser()
parser.add_option("-s", "--subject-id", dest="subjid", help="specify the subject id")
parser.add_option("-a", "--acquisition", type="int", dest="acq", help="specify acquisition number for this run")
parser.add_option("-c", "--counterbalance", type="int", dest="condition", help="specify which counter balancing to use [0-4]")
parser.add_option("-d", "--stims-dir", dest="stimsDir", default="stims", help="specify the directory from which to obtain stimuli")
parser.add_option("-m", "--motion", dest="motion", type="int", default=0, help="specify if motion should appear on the first or second block (0,1)")

# store the command line options in variables so we can
# avoid having to type options.___ everywhere
(options, args) 	        = parser.parse_args()
subjID 				= options.subjid
acq 				= options.acq
condition 			= options.condition
stimsDir 			= options.stimsDir
motion 				= options.motion

# verify that we have the information we need
if subjID == None or acq == None or condition == None:
    print "You must provide a Subject ID, Acquisition Number, and a Counter Balancing Number"
    parser.print_help()
    sys.exit()


screen = get_default_screen()
screen.parameters.bgcolor = (.5,.5,.5,0)

# define file names
file_name_plan = subjID + '-' + str(acq) + '-' + str(condition) + '-plan.txt'
file_name_para = subjID + '-' + str(acq) + '-' + str(condition) + '-para.txt'
file_name_data = subjID + '-' + str(acq) + '-' + str(condition) + '-data.txt'

# setup data file
datafile = open(file_name_data, 'a')
data_writer = csv.writer(datafile)

# calculate a few variables we need
mid_x = screen.size[0]/2.0
mid_y = screen.size[1]/2.0
max_vel = 5

# Setup Stimuli
fixation = FixationCross(
    position    = (screen.size[0]/2.0, screen.size[1]/2.0),
    size        = (36,36)
)

# stimuli_size = (int(screen.size[0]/stim_scaler), int(screen.size[0]/stim_scaler))
stimuli_size = (300, 300)

# get image directories
cur_directory = os.curdir
stims_dir = os.path.join(cur_directory, stimsDir)
stims_list = os.listdir(stims_dir)

stim_dirs = []

print "Stimulus and ID pairing, use to define counter balancing (+1 in paradigm files)"
for stims in stims_list:
    if os.path.isdir(os.path.join(stims_dir, stims)):
        stim_dirs.append(os.path.join(stims_dir, stims))
        print str(stim_dirs.index(os.path.join(stims_dir, stims))) + ": " + stims

# put stims into a massive stim array
final_stim_list = []
for i in range(len(stim_dirs)):
    final_stim_list.append([])

print "Found", range(len(stim_dirs)), "stimulus directories"

i = 0
for stim_dir in stim_dirs:
    stim_list = listDirectory(stim_dir, ['.jpg', '.JPG'])
    final_stim_list[i].extend(stim_list)
    i = i + 1

# Block description:
# F: Fixation
# 0: Attend to face   0% confound
# 1: Attend to face  25% confound
# 2: Attend to face  50% confound
# 3: Attend to face  75% confound
# 4: Attend to house  0% confound
# 5: Attend to house 25% confound
# 6: Attend to house 50% confound
# 7: Attend to house 75% confound     
if condition == 0:
    blocks = [2, 1, 5, 4, 0, 'F', 7, 6, 3]
elif condition == 1:
    blocks = [4, 3, 'F', 2, 0, 7, 5, 6, 1]
elif condition == 2:
    blocks = [0, 3, 'F', 5, 4, 6, 7, 1, 2]
elif condition == 3:
    blocks = [3, 'F', 1, 6, 2, 5, 4, 0, 7]
else:
    print "unknown counter balancing specified (" + str(condition) + "), exiting ... "
    sys.exit(2)

# PW 2012/11/27: If testting, start without fixation
if test_seq:
	blocks = [0, 1, 2, 3, 4, 5, 6, 7, 'F']

print "writing paradigm files for this condition ..."  

fp = open(file_name_para, 'w')
t_count = 0
for condition in blocks:
    #PW 2012/11/26
    for i in range(int(block_len/tr)):
        if condition == 'F':
	    cond_str = 0
	else:
	    if i < instruction_time / tr:
                cond_str = -1
            else:
	        cond_str = condition + 1
        fp.write(str(t_count) + ".0\t\t" + str(cond_str) + "\n")
        t_count = t_count + tr       
fp.close()
   
# create fixation viewport
viewport_fixation = Viewport ( screen=screen, stimuli=[ fixation ] )
viewport_stimuli = Viewport ( screen=screen, stimuli=[] )

# generate exp plan
print "loading images into memory ... "
exp_plan = []
#exp_plan_1back = []
block_count = 0
for block in blocks:
    block_count = block_count+1
    back_count = num_1back
    back_count_cfound = num_1back_cfound

    trial_has_motion = motion % 2
    motion = motion + 1
    # PW 2012/11/26: Permanently disable moving stimulus
    if disable_motion:
        trial_has_motion = 0
   
    # for the given block, select a random selection of images
    if block != 'F':
	alpha = block % 4 * 0.25
	if block < 4:
		stim_set = 0
		confound_set = 1
		instructions = "F"		
	else:
		stim_set = 1
		confound_set = 0
                instructions = "S"		
        try:
            image_list = random.sample(final_stim_list[stim_set], num_trials+num_1back_cfound)
	    confound_list = random.sample(final_stim_list[confound_set], num_trials+num_1back)
        except:
            print "number of trials > number of stimuli for current block"
            sys.exit(2)

    for trial in range(num_trials-num_1back-num_1back_cfound):
        if back_count > 0:
            do_1back = True
            do_1back_cfound = False
            back_count = back_count - 1
        else:
            do_1back = False
            if back_count_cfound > 0:
                do_1back_cfound = True
                back_count_cfound = back_count_cfound -1
            else:
                do_1back_cfound = False
       
        theta = random.choice(motion_vectors)
        
        if block == 'F':
            # create a fixation trial
            row = [ random.random()+block_count, '', False, 'fixation', condition, acq, trial_has_motion, theta, 'fixation', 0.0, '-', False]
        else:
            #image_file = random.choice(final_stim_list[block])
            image_file = image_list.pop()
	    confound_file = confound_list.pop()
            row = [random.random()+block_count, '', do_1back,image_file, condition, acq, trial_has_motion, theta, confound_file, alpha, instructions, do_1back_cfound]
           
        exp_plan.append(row)
        if do_1back:
            if block == 'F':
                exp_plan.append(row)
            else:
	        row2 = list(row)
	        row2[8] = confound_list.pop()
                #exp_plan_1back.append(row2)
                exp_plan.append(row2)
        elif do_1back_cfound:
	    if block == 'F':
                exp_plan.append(row)
            else:
                row2 = list(row)
	        row2[3] = image_list.pop()
                #exp_plan_1back.append(row2)
                exp_plan.append(row2)

#exp_plan.extend(exp_plan_1back)
exp_plan.sort()

# write the experiment plan to disk so we can compare it to behavioral data

planfile = open(file_name_plan, 'a')
plan_writer = csv.writer(planfile)
plan_writer.writerows(exp_plan)
planfile.close()

print "expected experiment time: " + str(len(exp_plan)*trial_dur)
print "ips: " + str(len(exp_plan)*trial_dur / tr)

# wait for trigger
instructions = Text(
    text    = "Waiting for trigger",
    font_size   = 32,
    color   = (1,1,1),
    anchor = 'center',
    position = (screen.size[0]/2, screen.size[1]/2),
)

instructions_attendFACE = Text(
    text    = "Attend to FACES",
    font_size   = 32,
    color   = (1,1,1),
    anchor = 'center',
    position = (screen.size[0]/2, screen.size[1]/2),
)

instructions_attendSCENE = Text(
    text    = "Attend to SCENES",
    font_size   = 32,
    color   = (1,1,1),
    anchor = 'center',
    position = (screen.size[0]/2, screen.size[1]/2),
)

cur_time = Text(
	text		= "",
	font_size 	= 15,
	color		= (.75,.75,.75),
	anchor		= 'lowerleft',
	position	= (0,0),
	)

viewport_instructions = Viewport( screen=screen, stimuli = [ instructions, cur_time ] )
attend_face = Viewport(screen=screen, stimuli = [instructions_attendFACE])
attend_scene = Viewport(screen=screen, stimuli = [instructions_attendSCENE])
p1 = Presentation(go_duration=('forever',), viewports=[viewport_instructions])
p1.add_controller(None,None,FunctionController(during_go_func=displayTime))
p1.parameters.handle_event_callbacks =  [ (pygame.locals.KEYDOWN, waitForTrigger) ]

# setup main experimental loop
loadStims 		= 0
wrote_response 	= 0

stimulus =      TextureStimulus(
                    anchor                  = 'center',
                    size                    = stimuli_size,
                    position                = (screen.size[0]/2.0, screen.size[1]/2.0),
                    texture_min_filter      = gl.GL_LINEAR,
                    shrink_texture_ok       = 1,
		    # PW 2012/11/26
                    mipmaps_enabled = False
                )

#p = Presentation(go_duration=(trial_dur*len(exp_plan), 'seconds'), viewports=[viewport_fixation])
p = Presentation(go_duration=(num_blocks * block_len, 'seconds'), viewports=[viewport_fixation])
p.parameters.handle_event_callbacks =  [ (pygame.locals.KEYDOWN, keydown) ]
p.add_controller(None,None,FunctionController(during_go_func=oneTrial))
#p.add_controller(stimulus,'position', FunctionController(during_go_func=get_target_position) )

exp_start_time = time.time()
p1.go()

exp_start_time = time.time()
p.go()
exp_end_time = time.time()

print exp_end_time - exp_start_time
datafile.close

