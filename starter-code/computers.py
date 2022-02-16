import numpy as np
import json
import time
from requests import get
import random
from time import sleep
from threading import Thread

# Initialization of type of node
LEADER = 0
CANDIDATE = 1
FOLLOWER = 2

# Wait before starting timer
TIME_BEFORE_TIMER_START = 5  # >= TIME_TO_SET_SERVERS

# Initialization of timeouts
TIMEOUT = 4
HEARTBEAT_TIMEOUT = 0.2  # HEARTBEAT_TIMEOUT < MIN_ELECTION_TIMEOUT
MIN_ELECTION_TIMEOUT = 1
MAX_ELECTION_TIMEOUT = 2


class FlightComputer:

    def __init__(self, state):
        self.state = state
        self.status = FOLLOWER
        self.election_time = time.time()
        self.current_stage_index = 0
        self.peers = []
        self.completed = True
        self.term = 0
        self.vote = 0
        self.stage_handlers = [
            self._handle_stage_1,
            self._handle_stage_2,
            self._handle_stage_3,
            self._handle_stage_4,
            self._handle_stage_5,
            self._handle_stage_6,
            self._handle_stage_7,
            self._handle_stage_8,
            self._handle_stage_9]
        self.stage_handler = self.stage_handlers[self.current_stage_index]
        self.election_timeout = 0
        self.reset_election_timeout()
        self.address = None
        self.inc_decide_action = 0
        self.inc_decide_state = 0
        self.address = 0
        self.leader_address = 0
        self.is_election_time = True
        self.step = 0
        self.suspected = {}
        self.potential_good_peers = []

    # Get current leader address
    def ask_leader_address(self):
        return self.leader_address

    # Set own address
    def add_own_address(self, _address):
        self.address = _address

    # Get own address
    def get_address(self):
        return self.address

    # Reset timeout of election
    def reset_election_timeout(self):
        self.election_timeout = random.uniform(MIN_ELECTION_TIMEOUT, MAX_ELECTION_TIMEOUT)

    # Add a new peer
    def add_peer(self, peer):
        self.peers.append(peer)
        self.suspected[str(peer)] = 0

    # Force a new election
    def new_election(self):
        self.is_election_time = True

    def _handle_stage_1(self):
        action = {"pitch": 90, "throttle": 1.0, "heading": 90, "stage": False, "next_state": False}
        if self.state["altitude"] >= 1000:
            action["pitch"] = 80
            action["next_stage"] = True

        return action

    def _handle_stage_2(self):
        action = {"pitch": 80, "throttle": 1.0, "heading": 90, "stage": False, "next_state": False}
        # Eject SRB's before the gravity turn
        if self.state["fuel_srb"] <= 1250:
            action["stage"] = True
            action["next_stage"] = True

        return action

    def _handle_stage_3(self):
        action = {"pitch": 80, "throttle": 1.0, "heading": 90, "stage": False, "next_state": False}
        # Eject 2nd SRB + Initial Gravity turn
        if self.state["fuel_srb"] <= 10:
            action["stage"] = True
            action["pitch"] = 60.0
            action["next_stage"] = True

        return action

    def _handle_stage_4(self):
        action = {"pitch": 80, "throttle": 1.0, "heading": 90, "stage": False, "next_state": False}
        # Turn
        if self.state["altitude"] >= 25000:
            action["pitch"] = 0
            action["throttle"] = 0.75
            action["next_stage"] = True

        return action

    def _handle_stage_5(self):
        action = {"pitch": 0, "throttle": 0.75, "heading": 90, "stage": False, "next_state": False}
        # Cut throttle when apoapsis is 100km
        if self.state["apoapsis"] >= 100000:
            action["throttle"] = 0.0
            action["next_stage"] = True

        return action

    def _handle_stage_6(self):
        action = {"pitch": 0, "throttle": 0.0, "heading": 90, "stage": False, "next_state": False}
        # Drop stage
        if self.state["altitude"] >= 80000:
            action["stage"] = True
            action["next_stage"] = True

        return action

    def _handle_stage_7(self):
        action = {"pitch": 0, "throttle": 0.0, "heading": 90, "stage": False, "next_state": False}
        # Poor man's circularisation
        if self.state["altitude"] >= 100000:
            action["throttle"] = 1.0
            action["next_stage"] = True

        return action

    def _handle_stage_8(self):
        action = {"pitch": 0, "throttle": 1.0, "heading": 90, "stage": False, "next_state": False}
        if self.state["periapsis"] >= 90000:
            action["throttle"] = 0.0
            action["next_stage"] = True

        return action

    def _handle_stage_9(self):
        self.completed = True

    # Find the action according to the current state
    def sample_next_action(self):
        return self.stage_handler()

    # Decide on state and action with the other peers based on a consensus
    def decide_on_state_and_action(self, state):
        action_decided = False
        state_decided = self.decide_on_state(state)
        if state_decided:
            action = self.sample_next_action()
            action_decided = self.decide_on_action(action)
        if action_decided == False:
            self.is_election_time = True
            return False
        else:
            return action

    # Find the current leader and decide on state action with this leader
    def find_leader(self, state):
        leader_address = self.leader_address
        my_address = self.address
        begin = time.time()
        while my_address != leader_address:
            try:
                url = f"http://{leader_address}/ask_leader_address"
                response = get(url, timeout = TIMEOUT)
                if response.status_code != 200:
                    return False, False
                    print("Unable to ask leader address")
                end = time.time()
                diff = end - begin
                if diff > TIMEOUT:
                    return False, False
                leader_address_ask = response.json()["leader_address_ask"]
                my_address = leader_address
                if leader_address_ask != leader_address:
                    my_address = leader_address
                    leader_address = leader_address_ask
            except Exception as e:
                return False, False
                print("Exception in find_leader (1): " + str(e))

        url = f"http://{leader_address}/decide_on_state_and_action"
        begin = time.time()
        try:
            response = get(url, data = json.dumps({"state": state}))
            end = time.time()
            diff = end - begin
            if diff > TIMEOUT:
                url2 = f"http://{leader_address}/new_election"
                response2 = get(url2)
            if response.status_code != 200:
                print("Error: " + str(response))
                return False, False
            decided_action = response.json()['decided_action']
            return decided_action, leader_address
        except Exception as e:
            # When the leader is not a correct leader (at the first election for example),
            # we force the leader to not send heartbeat => New election
            url = f"http://{leader_address}/new_election"
            response = get(url)
            print("Exception in find_leader (2): " + str(e))
            return False, False

    # Ask a peer to know if it accepts or not the state
    def ask_decide_on_state(self, peer, state):
        try:
            url = f"http://{peer}/acceptable_state"
            response = get(url, data = json.dumps({"state": state, "term": self.term, "step": self.step}),
                           timeout = TIMEOUT)
            if response.status_code != 200:
                print("Error (acceptations) in decide_on_state: " + str(response))
            self.inc_decide_state += response.json()['state_acceptable']
        except Exception as e:
            print("Exception in ask_decide_on_state: " + str(e))

    # Decide on state by asking the other peers if their accept or not the state
    def decide_on_state(self, state):
        self.inc_decide_state = self.acceptable_state(state, self.term, self.step)
        for peer in self.peers:
            Thread(target = self.ask_decide_on_state, args = (peer, state)).start()
        clock = time.time()
        while (time.time() - clock < (TIMEOUT / 2)):
            if (self.inc_decide_state / (len(self.peers) + 1) > 0.5):
                self.inc_decide_state = 0
                for peer in self.peers:
                    Thread(target = self.send_state, args = (peer, state)).start()

                self.deliver_state(state)
                return True
        return False

    # Broadcast the state
    def send_state(self, peer, state):
        try:
            url = f"http://{peer}/deliver_state"
            response = get(url, data = json.dumps({"state": state}), timeout = TIMEOUT)
            if response.status_code != 200:
                print("Error (deliver) in decide_on_state: " + str(response))
        except Exception as e:
            print("Exception in send_state: " + str(e))

    # Ask a peer to know if it accepts or not the action
    def ask_decide_on_action(self, peer, action):
        try:
            url = f"http://{peer}/acceptable_action"
            response = get(url, data = json.dumps({"action": action, "term": self.term, "step": self.step}),
                           timeout = TIMEOUT)
            if response.status_code != 200:
                print("Error (acceptations) in decide_on_action: " + str(response))
            if response.json()['action_acceptable'] == True:
                self.inc_decide_action += response.json()['action_acceptable']
                self.potential_good_peers.append(str(peer))
        except Exception as e:
            print("Exception in ask_decide_on_action:" + str(e))

    # Decide on action by asking the other peers if their accept or not the action
    def decide_on_action(self, action):
        self.inc_decide_action = self.acceptable_action(action, self.term, self.step)
        for peer in self.peers:
            Thread(target = self.ask_decide_on_action, args = (peer, action)).start()
        clock = time.time()
        while time.time() - clock < (TIMEOUT / 2) - 1:
            if self.inc_decide_action / (len(self.peers) + 1) > 0.5:
                self.inc_decide_action = 0
                for peer in self.peers:
                    if peer in self.potential_good_peers and self.suspected[str(peer)] != 0:
                        self.suspected[str(peer)] -= 1
                    elif peer not in self.potential_good_peers and self.suspected[str(peer)] < 5:
                        self.suspected[str(peer)] += 1
                for peer in self.peers:
                    Thread(target = self.send_action, args = (peer, action)).start()
                self.deliver_action(action)
                self.potential_good_peers = []
                print("Action was decided by consensus")
                return True
        self.potential_good_peers = []
        return False

    # Broadcast the action
    def send_action(self, peer, action):
        try:
            url = f"http://{peer}/deliver_action"
            response = get(url, data = json.dumps({"action": action}), timeout = TIMEOUT)
            if response.status_code != 200:
                print("Error (deliver) in decide_on_action: " + str(response))
        except Exception as e:
            print("Exception in send_action: " + str(e))

    # Accept or not the state
    def acceptable_state(self, state, _term, _step):
        if (self.term <= _term) and (self.step <= _step):
            self.term = _term
            self.step = _step
            return True
        return False

    # Accept or not the action
    def acceptable_action(self, action, _term, _step):
        if (self.term <= _term) and (self.step <= _step):
            self.term = _term
            self.step = _step
            our_action = self.sample_next_action()
            if our_action is None and action is None:
                return True
            if our_action is None and action is not None:
                return False
            if our_action is not None and action is None:
                return False
            for k in our_action.keys():
                if our_action[k] != action[k]:
                    return False
            return True
        return False

    # Deliver the action
    def deliver_action(self, action):
        if action != None and "next_stage" in action and action["next_stage"]:
            self.current_stage_index += 1
            self.stage_handler = self.stage_handlers[self.current_stage_index]

    # Deliver the state
    def deliver_state(self, state):
        self.state = state

    # Update information when the computer receives a valid heartbeat
    def heartbeat_message(self, state, _address, _term, _step):
        if self.term < _term:
            self.step = 0
        if self.term <= _term and self.step < _step:
            self.term = _term
            self.state = state
            self.leader_address = _address
            self.election_time = time.time()
            self.reset_election_timeout()
            self.status = FOLLOWER
            self.step = _step

    # Get the state
    def get_state(self):
        return self.state

    # Vote for the candidate if the request is valid
    def request_vote(self, candidate_term, candidate_address):
        if self.term < candidate_term and self.suspected[str(candidate_address)] < 2:
            self.reset_election_timeout()
            self.election_time = time.time()
            self.term = candidate_term
            self.status = FOLLOWER
            return True

        return False

    # Ask a peer for voting
    def ask_vote(self, peer, term):
        try:
            while self.status == CANDIDATE and self.term == term:
                url = f"http://{peer}/request_vote"
                response = get(url, data = json.dumps({"candidate_term": self.term, "candidate_address": self.address}),
                               timeout = self.election_timeout)
                if response.status_code != 200:
                    print("Error (request_vote) in ask_vote(): " + str(response))
                if response.json()['has_voted_for_leader']:
                    self.increment_vote()
                break
        except Exception as e:
            print("Exception in ask_vote: " + str(e))

    # Increment vote and verify if the computer can become a leader
    def increment_vote(self):
        if self.status == CANDIDATE:
            self.vote += 1
            if self.vote / (len(self.peers) + 1) > 0.5:
                vote = self.vote
                self.vote = 0
                print(f"{self.address}: Becomes Leader by receiving " + str(vote) + " votes")
                self.status = LEADER
                self.leader_address = self.address
                self.is_election_time = False
                self.step = 0
                self.step += 1
                for peer in self.peers:
                    self.send_heartbeat_message(peer, self.state)

    # Send heartbeat message to a peer
    def send_heartbeat_message(self, peer, state):
        try:
            url = f"http://{peer}/heartbeat_message"
            response = get(url, data = json.dumps(
                {"state": self.state, "leader_address": self.address, "term": self.term, "step": self.step}),
                           timeout = TIMEOUT)
            if response.status_code != 200:
                print("Error (deliver) herbeat message: " + str(response))
        except Exception as e:
            print("Exception in send_herbeat_message): " + str(e))

    # Timer to know if the computer must start a new election or send 
    # heartbeats when it is a leader
    def timer(self):
        sleep(TIME_BEFORE_TIMER_START)
        while True:
            current_time = time.time()
            if self.status != LEADER:
                if (current_time - self.election_time) > self.election_timeout:
                    print(f"{self.address}: Becomes Candidate at term " + str(self.term))
                    self.status = CANDIDATE
                    self.term += 1
                    self.election_time = current_time
                    self.reset_election_timeout()
                    self.vote = 0
                    self.increment_vote()

                    for peer in self.peers:
                        Thread(target = self.ask_vote, args = (peer, self.term)).start()
            else:
                if (current_time - self.election_time) > HEARTBEAT_TIMEOUT and not self.is_election_time:
                    self.election_time = current_time
                    self.vote = 0
                    self.step += 1
                    for peer in self.peers:
                        Thread(target = self.send_heartbeat_message, args = (peer, self.state)).start()


class FullThrottleFlightComputer(FlightComputer):

    def __init__(self, state):
        super(FullThrottleFlightComputer, self).__init__(state)

    def sample_next_action(self):
        action = super(FullThrottleFlightComputer, self).sample_next_action()
        if action != None:
            action["throttle"] = 1.0

        return action


class RandomThrottleFlightComputer(FlightComputer):

    def __init__(self, state):
        super(RandomThrottleFlightComputer, self).__init__(state)

    def sample_next_action(self):
        action = super(RandomThrottleFlightComputer, self).sample_next_action()
        if action != None:
            action["throttle"] = np.random.uniform()

        return action


class SlowFlightComputer(FlightComputer):

    def __init__(self, state):
        super(SlowFlightComputer, self).__init__(state)

    def sample_next_action(self):
        action = super(SlowFlightComputer, self).sample_next_action()
        time.sleep(np.random.uniform() * 10)  # Seconds

        return action


class CrashingFlightComputer(FlightComputer):

    def __init__(self, state):
        super(CrashingFlightComputer, self).__init__(state)

    def sample_next_action(self):
        try:
            action = super(SlowFlightComputer, self).sample_next_action()
            # 1% probability of a crash
            if np.random.unifom() <= 0.01:
                raise Exception("Flight computer crashed")
            return action
        except Exception as e:
            action = {"pitch": -1, "throttle": -1, "heading": -1, "stage": False, "next_state": False}
            return action


def allocate_random_flight_computer(state):
    computers = [
        FullThrottleFlightComputer,
        RandomThrottleFlightComputer,
        SlowFlightComputer,
        CrashingFlightComputer,
    ]

    return computers[np.random.randint(0, len(computers))](state)
