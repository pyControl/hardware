# Task for calibrating solenoids on grid maze setups. The calibration process works by measuring
# the change in weight of the water reservoir when water is released by each solenoids.  For each
# reward port, the volume of  water released for a set of different release durations is measured.
# A seperate script "calibrated_release_times.py" is then used to process the resulting data file,
# generating linear fits mapping reward volume to release duration for each port.  To obtain
# accurate measurments of small release volumes, the weight change is measured across a set of
# multiple releases, with the number of releases automatically determined to generate a target
# total weight change.

# Calibration process
# 1. Upload the task to the maze, enter a subject ID so the data is saved, and run the task.
# 2. Ensure the reservoir is full, and not touching the enclosure wall or cables.
# 3. Open the 'Controls' dialog and trigger the event `tare` to zero the load cell.
# 4. Calibrate the load cell using a known calibration weight:
#   i. Place a small object of known weight (e.g. a coin) on top of the reservoir.
#   ii. Using the controls dialog, set variable `calibration_weight` to the object's weight in
#       grams, then trigger the `calibrate` event. Check the load cell is correctly calibrated
#        by triggering the `weigh` event with the object on and off the reservoir.
#   iii. Remove the object from the reservoir.
# 5. Trigger the `go` event to start the calibration, the task will cycle through the set of release
#    durations, and through reward ports for each release duration. The task pauses and waits for the
#    'go' event between release durations to allow water to be removed from the ports. The calibration
#    task stops automatically when all release durations have been run.
# 6. Transfer the pyControl data file to the folder `autocalibration_data`, then run the python script
# `autocalibration_script.py` to generate the linear fits used for solenoid calibration.

# For more information see: https://github.com/pyControl/hardware/blob/master/GridMaze/solenoid_autocalibation

from pyControl.utility import *
from devices import *

# Define hardware

maze = Grid_maze_3x3()

load_cell = Load_cell(maze.port_1, scale=14000)

# States and events.

states = ["wait_for_go", "release", "post_release", "pre_release", "calibration_init"]

events = ["tare", "calibrate", "weigh", "go", "timer_event"]

initial_state = "wait_for_go"

# Parameters

v.pokes_to_calibrate = sorted([ev[:2] for ev in maze.events if ev[-2:] == "in"])  # ["A1", "B1", "B3"] #
v.calibration_weight = 1  # Weight of reference object used for load cell calibration.
v.release_durations = [50, 100, 150, 200]  # Set of release durations to measure (ms)
v.target_weight = 0.2  # Target weight change for measurments, determines number of releases.
v.max_releases = 100  # Maximum number of releases if target weight is not reached.
v.n_release_per_batch = 4  # Number of releases between checks for whether target weight reached.
v.times = 6  # Number of times each individual load cell measurement is repeated.

# Variables
v.release_duration = None  # Current release duration being tested/
v.n_release = 0  # Release number for current calibration.
v.batch_count = 0  # Release number in current batch between weight checks.
v.pre_weight = 0  # Weight before any releases for current calibration.
v.poke = None  # Which poke is being calibrated.
v.release_weight = None  # Release weight fo current calibration.


# State behaviour functions


def wait_for_go(event):
    # wait for user inpup.
    if event == "tare":  # Re-zero the load cell.
        load_cell.tare()
    elif event == "calibrate":  # Calibrate the load cell using a calibration weight.
        load_cell.calibrate(weight=v.calibration_weight)
        print("Scale: {}".format(load_cell.SCALE))
    elif event == "weigh":  # Measure and print the current weight.
        print(load_cell.weigh(times=v.times))
    elif event == "go":  # Continue with calibration process.
        timed_goto_state("calibration_init", 100)


def calibration_init(event):
    # Initialise a given release duration, wait for user input to go.
    if event == "entry":
        if len(v.release_durations) > 0:
            v.pokes = v.pokes_to_calibrate.copy()
            v.release_duration = v.release_durations.pop(0)
            print("Ready to calibrate release duration: {}, press go.".format(v.release_duration))
        else:
            print("Calibration finished")
            stop_framework()
    elif event == "go":
        goto_state("pre_release")


def pre_release(event):
    # Measure weight before any releases and initialise variables.
    if event == "entry":
        v.poke = v.pokes.pop(0)
        maze.LED_on(v.poke)
        v.pre_weight = load_cell.weigh(v.times)
        v.n_release = 0
        v.batch_count = 0
        timed_goto_state("release", 100)


def release(event):
    # trigger releases until target weight has been reached.
    if event == "entry":
        maze.SOL_on(v.poke)
        v.batch_count += 1
        v.n_release += 1
        set_timer("timer_event", v.release_duration)
    elif event == "timer_event":
        maze.SOL_off(v.poke)
        if v.batch_count < v.n_release_per_batch:  # Continue in batch.
            timed_goto_state("release", 50)
        else:  # End of batch, check if target weight has been reached.
            release_weight = v.pre_weight - load_cell.weigh(v.times)
            print(release_weight)
            if (release_weight > v.target_weight) or (v.n_release > v.max_releases):  # Releases completed
                timed_goto_state("post_release", 100)
            else:  # New batch
                v.batch_count = 0
                timed_goto_state("release", 50)


def post_release(event):
    # take weight measurment used for calibration and output to data file.
    if event == "entry":
        maze.LED_off(v.poke)
        v.release_weight = v.pre_weight - load_cell.weigh(v.times)
        print_variables(["poke", "release_duration", "n_release", "release_weight"])
        if len(v.pokes) > 0:
            timed_goto_state("pre_release", 100)
        else:
            timed_goto_state("calibration_init", 100)
