from collections import namedtuple
import numpy as np
from time import sleep
from planner import Request
from web3 import Web3

Position = namedtuple(
    "Position", ("x", "y")
)
Volume = namedtuple(
    "Volume", ("length","width","height")
)

class Drone:

    def __init__(self, position, max_payload, max_volume, distance_left, speed, set_up_time, drop_off_time, address, vehicle, request, custodian):
        self.position = position
        self.max_payload = max_payload
        self.max_volume = max_volume
        self.distance_left = distance_left
        self.speed = speed
        self.set_up_time = set_up_time
        self.drop_off_time = drop_off_time
        self.time_for_task = 0
        self.address = address
        #self.private_key = private_key
        self.vehicleOracle = vehicle
        self.requestOracle = request
        self.custodian = custodian
        self.waypoints = []
        self.sequence = self.custodian.functions.OpenedSeq().call() + 1 # newly opened sequence + 1 (first valid sequence)

    def __str__(self):
        return f"Drone #{self.name} with address: {self.address}"

    def get_next_wp(self):
        if self.custodian.functions.campHasFinished(self.sequence).call() != True:
            return
        addresses = self.vehicleOracle.functions.getVehiclesAddresses(self.sequence).call()
        index = 0
        for address in addresses:
            if address == self.address:
                self.order = index
                break
            index += 1
        if index == len(addresses):
            return
        
        solution = self.custodian.functions.getVotingBySeq(self.sequence).call()
        solution = solution[2]                                          # Discard winner and cost
        
        req_1 = self.requestOracle.functions.getRequests_1(self.sequence).call()
        req_2 = self.requestOracle.functions.getRequests_2(self.sequence).call()
        requests = []
        for i in range(len(req_1[0])):
            requests.append(Request(Position(req_1[0][i],req_1[1][i]),\
                                    Position(req_1[2][i],req_1[3][i]),\
                                    req_2[0][i],\
                                    Volume(req_2[1][i],req_2[2][i],req_2[3][i])))
        
        init = self.order * len(requests)
        end  = init + len(requests)
        for index in range(init, end):
            if solution[index] == 0:
                continue
            self.waypoints.append(requests[solution[index] - 1])
            
        self.sequence += 1
        

def move(drone, web3):        
    # Send data to the blockchain for the first time
    tx_hash = drone.vehicleOracle.functions.setVehicleProperties(drone.position.x, drone.position.y,\
                                                           drone.max_payload,\
                                                           drone.max_volume.length, drone.max_volume.width, drone.max_volume.height,\
                                                           drone.distance_left,\
                                                           drone.speed,\
                                                           drone.set_up_time,\
                                                           drone.drop_off_time,\
                                                           drone.time_for_task).transact({'from':drone.address})
    web3.eth.waitForTransactionReceipt(tx_hash)
    
    while True:
        drone.get_next_wp()
        if len(drone.waypoints) == 0:
            sleep(2)
            continue
        time_1 = np.sqrt((drone.position.x - drone.waypoints[0].source.x)**2 +\
                         (drone.position.y - drone.waypoints[0].source.y)**2) /\
                         drone.speed + drone.set_up_time
        
        time_2 = np.sqrt((drone.waypoints[0].destination.x - drone.waypoints[0].source.x)**2 +\
                         (drone.waypoints[0].destination.y - drone.waypoints[0].source.y)**2) /\
                         drone.speed + drone.drop_off_time
        #print('Drone order',drone.order,'moving to source (',drone.waypoints[0].source.x,',',drone.waypoints[0].source.x,')')
        sleep(time_1/4)                             # Might want to divide the time to speed up simulation
        # Update the remaining distance
        # Not implemented now
        # Might add a sleep for refueling and add it to the drone's time_to_task !!!
        # One or more refueling station can be added and treated as a request
        # Then they can be appended every time the drone's distance left is close to the sum of waypoints to traverse
        time = 0
        for request in drone.waypoints[1:]:
           time += np.sqrt((request.destination.x - request.source.x)**2\
                          + (request.destination.y - request.source.y)**2)
        drone.time_for_task = time / drone.speed + (drone.set_up_time + drone.drop_off_time)*len(drone.waypoints)
        # Send transaction to update position and distance
        new_Position = Position(drone.waypoints[0].source.x,drone.waypoints[0].source.y)
        drone.position = new_Position
        drone.vehicleOracle.functions.updateVehicleProperties(drone.position.x, drone.position.y, int(drone.distance_left), int(drone.time_for_task + time_2)).transact({'from':drone.address})
        web3.eth.waitForTransactionReceipt(tx_hash)
        # Perform the last leg for delivery
        #print('Drone order',drone.order,'moving to destination (',drone.waypoints[0].destination.x,',',drone.waypoints[0].destination.x,')')
        sleep(time_2/4)
        new_Position = Position(drone.waypoints[0].destination.x,drone.waypoints[0].destination.y)
        drone.position = new_Position
        drone.vehicleOracle.functions.updateVehicleProperties(drone.position.x, drone.position.y, int(drone.distance_left), int(drone.time_for_task)).transact({'from':drone.address})
        web3.eth.waitForTransactionReceipt(tx_hash)
        
        drone.waypoints = drone.waypoints[1:]
        
        # Send money back to the source in order to keep the balance consistent