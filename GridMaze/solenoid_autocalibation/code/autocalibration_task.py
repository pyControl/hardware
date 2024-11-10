# This pyControl task is run on the maze hardware to run the autocalibration procedure.
# The process for autocalibrating a maze is:
#   1. Upload the task to the maze, enter a subject ID so the data is saved, and run the task.
#   2. Ensure the reservoir is full.
#   3. Open the 'Controls' dialog and trigger the event 'tare' to zero the load cell.
#   4. Get a small object of known weight (e.g. a coin) and place on top of the reservoir.
#   5. Using the controls dialog, set variable 'calibration_weight' to the weight of the object,
#      then trigger the event 'calibrate' to calibrate the load cell. You can check the load cell is
#      correctly calibrated by triggering the 'weigh' event with the object on and off the resorvoir.
#   6. Remove the object from the reservoir.
#   7. Trigger the 'go' event to start the calibration, the task will cycle through all the solenoids
#      triggering multiple releases at a set of specified release durations and measuring the weight
#      change of the reservoir.
#   8. When the calibration process has finished, stop the task and remove the released water from the
#      ports using a syringe.
#   9. Transfer the pyControl data file to the folder autocalibration_data, then run the
#      python script 'autocalibration_script.py' to generate the linear fits used for solenoid calibration.

from pyControl.utility import *
from devices import *

# Define hardware (normally done in seperate hardware definition file).

maze = Grid_maze_7x7()
load_cell = Load_cell(maze.port_2, scale=13583)  # recalibrated from 13090

# States and events.

states = ["wait_for_go", "release", "post_release", "pre_release", "calibration_init"]

events = ["tare", "calibrate", "weigh", "go", "timer_event"]

initial_state = "wait_for_go"

# variables

v.pokes_to_calibrate = sorted([ev[:2] for ev in maze.events if ev[-2:] == "in"])

# v.pokes_to_calibrate = ["B2", "B4", "B6", "D2", "D4", "D6", "F2", "F4", "F6"]

v.calibration_weight = 1
v.release_durations = [30, 60, 90]  # Release durations to measure (ms)
v.release_duration = None
v.n_releases = [40, 20, 15]  # Number of release of each duration.
v.n_release = None
v.release_count = 0
v.pre_weight = 0
v.poke = None
v.release_weight = None

# State behaviour functions


def wait_for_go(event):
    if event == "tare":
        load_cell.tare()
    elif event == "calibrate":
        load_cell.calibrate(weight=v.calibration_weight)
        print("Scale: {}".format(load_cell.SCALE))
    elif event == "weigh":
        print(load_cell.weigh(times=1))
    elif event == "go":
        timed_goto_state("calibration_init", 100)


def calibration_init(event):
    if event == "entry":
        if len(v.release_durations) > 0:
            v.pokes = v.pokes_to_calibrate.copy()
            v.release_duration = v.release_durations.pop(0)
            v.n_release = v.n_releases.pop(0)
            timed_goto_state("pre_release", 100)
        else:
            timed_goto_state("wait_for_go", 100)


def pre_release(event):
    if event == "entry":
        v.poke = v.pokes.pop(0)
        maze.LED_on(v.poke)
        v.pre_weight = load_cell.weigh()
        timed_goto_state("release", 100)


def release(event):
    if event == "entry":
        if v.release_count < v.n_release:
            maze.SOL_on(v.poke)
            v.release_count += 1
            set_timer("timer_event", v.release_duration)
        else:
            v.release_count = 0
            timed_goto_state("post_release", 100)
    elif event == "timer_event":
        maze.SOL_off(v.poke)
        timed_goto_state("release", 50)


def post_release(event):
    if event == "entry":
        maze.LED_off(v.poke)
        v.release_weight = abs(load_cell.weigh() - v.pre_weight)
        print_variables(["poke", "release_duration", "n_release", "release_weight"])
        if len(v.pokes) > 0:
            timed_goto_state("pre_release", 100)
        else:
            timed_goto_state("calibration_init", 100)
