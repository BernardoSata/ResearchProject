from os import chdir
chdir("/home/bernardo/Research Project/PlanningCustodian_3/Simulation")
import numpy as np
from time import sleep, time
from planner import Drone, Request, computeAllocation
from collections import namedtuple

Position = namedtuple(
    "Position", ("x", "y")
)
Volume = namedtuple(
    "Volume", ("length","width","height")
)

def vote(address, map_size, custodian, requestOracle, vehicleOracle, cycle, max_time, timeout, web3, simulation_ratio, number_of_cycles):
    
    filter_seed=custodian.events.newVoterSeed.createFilter(fromBlock=0, toBlock='latest')
    eventlist = filter_seed.get_all_entries()
    for event in eventlist:
        if(event['args']['voter'] == address):
            seed = event['args']['seed']
    
    sequence = 0
    while sequence == 0:
        sequence = custodian.functions.OpenedSeq().call()
        sleep(2)
        
    # Launch a thread for the dispute phase (reads the events and runs the computation again)
    
    while sequence < number_of_cycles:
        timer = time() + cycle
        # Get the current set of requests
        req_1 = requestOracle.functions.getRequests_1(sequence).call()
        req_2 = requestOracle.functions.getRequests_2(sequence).call()
        if(len(req_1[0]) == 0):
            print("No requests were found")
            sleep(5)
            continue
        requests = []
        for i in range(len(req_1[0])):
            requests.append(Request(Position(req_1[0][i],req_1[1][i]),\
                                    Position(req_1[2][i],req_1[3][i]),\
                                    req_2[0][i],\
                                    Volume(req_2[1][i],req_2[2][i],req_2[3][i])))
        
        # Get the current set of vehicles    
        veh_1 = vehicleOracle.functions.getVehicles_1(sequence).call()
        veh_2 = vehicleOracle.functions.getVehicles_2(sequence).call()
        if(len(veh_1[0]) == 0):
            print("No vehicles were found")
            sleep(5)
            continue
        vehicles = []
        for i in range(len(veh_1[0])):
            vehicles.append(Drone(i,\
                                  Position(veh_1[0][i],veh_1[1][i]),\
                                  veh_1[2][i],\
                                  Volume(veh_1[3][i],veh_1[4][i],veh_1[5][i]),\
                                  veh_2[0][i],veh_2[1][i],veh_2[2][i],veh_2[3][i],veh_2[4][i]))
        
        #print('Computing solution for',len(requests),'requests and',len(vehicles),'vehicles')
        np.random.seed(seed)
        root_f = computeAllocation(requests, vehicles, max_time, timeout, map_size)
        gamma = 0.9    
        index = 0
        action_scores = np.zeros((len(root_f.children_lists),1))
        for children_list in root_f.children_lists:
            if len(children_list[0][0].actions) == 0:       # Family not explored yet (do not affect value computation)
                action_scores[index] = 1e100
            else:
                prob = []
                values = []
                for child in children_list:
                    prob.append(child[1])
                    values.append(child[0].value)
                    action_scores[index] = np.sum(np.asarray(prob) * np.asarray(np.asarray(root_f.actions[index][2]) + gamma*np.asarray(values)))\
                    / np.sum(prob)
                index += 1
                    
        best_child = np.argmin(action_scores)
        solution = []
        for elem in root_f.actions[best_child][0]:
            solution.append(int(elem))
         
        print('Voting from',address,'gene:',solution)
        tx_hash = custodian.functions.acceptVote(int(np.min(action_scores)), solution).transact({'from':address, 'gas':3000000})
        web3.eth.waitForTransactionReceipt(tx_hash)
        
        sequence += 1
        sleep((timer - time())/simulation_ratio)