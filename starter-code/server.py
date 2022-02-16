from flask import Flask, request, jsonify
import argparse
from computers import *
import ast
import logging
from threading import Thread

app = Flask(__name__)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

def parse_arguments():
    parser = argparse.ArgumentParser("Parser")

    parser.add_argument("--state", type=str, default=None,
                        help="Sets the state of the computer.")
    parser.add_argument("--port", type=int, default=4000,
                        help = "Port on which the flask application runs")
    parser.add_argument("--address", type=str, default=None,
                        help="Address on which the flask application runs")
    parser.add_argument("--is_correct", type=str,
                        help = "Whether the flight computer is correct")
    arguments, _ = parser.parse_known_args()

    return arguments

arguments = parse_arguments()
computer = None
if arguments.is_correct != "0":
    computer = FlightComputer(state = ast.literal_eval(arguments.state))
else:
    computer = allocate_random_flight_computer(state = ast.literal_eval(arguments.state))

computer.add_own_address(arguments.address)

# Add the received peers to the computer
@app.route("/add_peer")
def add_peer():
    peer = request.get_json(force = True)['peer']
    computer.add_peer(peer)
    return jsonify({'peer_added': True})

# # Change its own address
# @app.route("/add_own_address")
# def add_own_address():
#     own_address = request.get_json(force = True)['own_address']
#     computer.add_own_address(own_address)
#     return jsonify({'own_address_added': True})

# Find the current leader address of the computer
@app.route("/ask_leader_address")
def ask_leader_address():
    leader_address = computer.ask_leader_address()
    return jsonify({'leader_address_ask': leader_address})

# Sample next action from the computer
@app.route("/sample_next_action")
def sample_next_action():
    action = computer.sample_next_action()
    return jsonify({"action": action})

# Decide on state and action
@app.route("/decide_on_state_and_action")
def decide_on_state_and_action():
    state = request.get_json(force = True)['state']
    decided_action = computer.decide_on_state_and_action(state)
    return jsonify({"decided_action": decided_action})

# Find the leader among all the computers
@app.route("/find_leader")   
def find_leader():
    state = request.get_json(force = True)['state']
    decided_action, leader_address = computer.find_leader(state)
    return jsonify({"decided_action": decided_action, "leader_address": leader_address})

# Accept or not the state received
@app.route("/acceptable_state")
def acceptable_state():
    state = request.get_json(force = True)['state']
    term = request.get_json(force = True)['term']
    step = request.get_json(force = True)['step']
    state_acceptable = computer.acceptable_state(state, term, step)
    return jsonify({"state_acceptable": state_acceptable})

# Accept or not the action received
@app.route("/acceptable_action")
def acceptable_action():
    action = request.get_json(force = True)['action']
    term = request.get_json(force = True)['term']
    step = request.get_json(force = True)['step']
    action_acceptable = computer.acceptable_action(action, term, step)
    return jsonify({"action_acceptable": action_acceptable})

# Deliver the state
@app.route("/deliver_state")
def deliver_state():
    state = request.get_json(force = True)['state']
    computer.deliver_state(state)
    return jsonify({"state_delivered": True})

# Deliver the action
@app.route("/deliver_action")
def deliver_action():
    action = request.get_json(force = True)['action']
    computer.deliver_action(action)
    return jsonify({"action_delivered": True})

# Return a vote for the candidate (True or False)
@app.route("/request_vote")
def request_vote():
    candidate_term = request.get_json(force = True)['candidate_term']
    candidate_address = request.get_json(force = True)['candidate_address']
    has_voted_for_leader = computer.request_vote(candidate_term, candidate_address)
    return jsonify({"has_voted_for_leader": has_voted_for_leader})

# Update the computer when received information from leader
@app.route("/heartbeat_message")
def heartbeat_message():
    state = request.get_json(force = True)['state']
    leader_address = request.get_json(force = True)['leader_address']
    term = request.get_json(force = True)['term']
    step = request.get_json(force = True)['step']
    computer.heartbeat_message(state, leader_address, term, step)
    return jsonify({"state": True})

# New election
@app.route("/new_election")
def new_election():
    computer.new_election()
    return jsonify({"election": True})

if __name__ == "__main__":
    Thread(target=computer.timer).start()
    app.run(port=arguments.port, debug=False)