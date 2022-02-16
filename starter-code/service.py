import subprocess32
import json
from requests import get
from time import sleep
import random

TIMEOUT = 8
TIME_TO_SET_SERVERS = 3

class Service:

    def __init__(self, n_correct_fc, n_incorrect_fc, state):
        ip = "127.0.0.1"
        port = 4000
        self.addresses = []
        self.servers = []

        # Initialize the servers with correct computers
        for _ in range(n_correct_fc):
            port += 1
            self.addresses.append(f"{ip}:{port}")
            server = subprocess32.Popen(
                ["python", "starter-code/server.py",
                 "--port", str(port),
                 "--address", str(self.addresses[-1]),
                 "--state", str(state)])
            self.servers.append(server)

        # Initialize the servers with incorrect computers
        for _ in range(n_incorrect_fc):
            port += 1
            self.addresses.append(f"{ip}:{port}")
            server = subprocess32.Popen(
                ["python", "starter-code/server.py",
                 "--port", str(port),
                 "--address", str(self.addresses[-1]),
                 "--state", str(state),
                 "--is_correct", str(0)])
            self.servers.append(server)

        # Sleep 3 seconds so that each server has enough time to be set
        # before any connection to these servers
        sleep(TIME_TO_SET_SERVERS)

        # Add the peers for the consensus protocol to each computer. 
        # Each computer will then know all the associated peers.
        for address in self.addresses:
            for peer_address in self.addresses:
                if address != peer_address:
                    url = f"http://{address}/add_peer"
                    response = get(url, data = json.dumps({"peer": peer_address}), timeout = TIMEOUT)
                    if response.status_code != 200:
                        print("Unable to send peer address")
                # else :
                #     url = f"http://{address}/add_own_address"
                #     response = get(url, data = json.dumps({"own_address": peer_address}), timeout = TIMEOUT)
                #     if response.status_code != 200:
                #         print("Unable to send own address")

        # Select a first leader that will change after
        sleep(4)
        self.leader_address = self.addresses[0]

    # Decide on state and on action
    def decide_on_state_and_action(self, state):
        address = self.leader_address
        while True:
            try:
                url = f"http://{address}/find_leader"
                response = get(url, data = json.dumps({"state": state}))
                if response.status_code != 200:
                    print("Error: " + str(response))
                    address = random.choice(self.addresses)
                elif response.json()["decided_action"] == False:
                    address = random.choice(self.addresses)
                else:
                    self.leader_address = response.json()["leader_address"]
                    return response.json()["decided_action"]
            except Exception as e:
                address = random.choice(self.addresses)

    # Kill all the servers that are running
    def __del__(self):
        for server in self.servers:
            server.kill()
