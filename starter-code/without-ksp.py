import argparse
import math
import pickle
import time
from typing import List

from service import *
from computers import *

# Load the pickle files
actions = pickle.load(open("data/actions.pickle", "rb"))
states = pickle.load(open("data/states.pickle", "rb"))
timestep = 0

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument("--correct-fraction", type=float, default=1.0, help="Fraction of correct flight computers (default 1.0).")
parser.add_argument("--flight-computers", type=int, default=3, help="Number of flight computers (default: 3).")
arguments, _ = parser.parse_known_args()

# Find the state corresponding to the timestep
def readout_state():
    return states[timestep]

# Verify that the action decided is the same as in the actions array
def execute_action(action):
    for k in action.keys():
        assert(action[k] == actions[timestep][k])

# Allocate a class Service responsible of the allocations of the
# flight computers (servers)
def allocate_service(arguments):
    n_fc = arguments.flight_computers
    n_correct_fc = math.ceil(arguments.correct_fraction * n_fc)
    n_incorrect_fc = n_fc - n_correct_fc
    initial_state = readout_state()
    return Service(n_correct_fc, n_incorrect_fc, initial_state)

# Initialization
service = allocate_service(arguments)
complete = False

# We have decided to create a list containing the important timesteps
listT = [0, 3831, 3832, 3833, 8415, 8416, 8417, 13802, 13803, 13804, 20319, 20320, 20321, 32290, 32291, 32292, 45137, 45138, 45139, 72798, 72799, 72800, 84572, 84573, 84574]
#listT += list(range(listT[-1] + 1, listT[-1] + 76))
convergence_time = []

# Launch the algorithm
try:
    j = 0
    while not complete: #and timestep < 100:
        # Use the list for the timestep. However, you can use the line 'timestep += 1' if you
        # want a timestep that increases slower (it can take a lot of time to compute)
        timestep = listT[j]
        #timestep += 1

        # Find the state corresponding to the timestep
        state = readout_state()

        print("-------------------------------------" + str(timestep) + "-------------------------------------")
        start = time.time()
        # Consensus on the action according to the state sent by the rocket
        action = service.decide_on_state_and_action(state)
        convergence_time.append(time.time() - start)
        print("Action decided: " + str(action))
        print("Action in actions array: " + str(actions[timestep]))
        print("\n")

        # It is the end, there is no more action
        if action is None:
            complete = True
            continue
        else: 
            j += 1
            execute_action(action)

except Exception as e:
    print(e)

if complete:
    print("-------------------------------------Success!-------------------------------------")
else:
    print("-------------------------------------Fail!-------------------------------------")

file = open(f"convergence_times/convergence_time_correct_fraction_{arguments.correct_fraction}.txt", "a")
for l in convergence_time:
    file.writelines(str(l)+",")
file.close()