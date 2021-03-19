from itertools import permutations
from copy import deepcopy
import numpy as np
#import plannerFull

def get_score(allocation, vehicles, requests):
        total_time = np.zeros((len(vehicles),1))
        veh = deepcopy(vehicles)
    
        for i in range(len(veh)):
            for j in range(len(requests)):
                req_index = (int) (allocation[i * len(requests) + j])
                if req_index != 0:
                    req_index -= 1
                    added_distance = np.sqrt((veh[i].position.x - requests[req_index].source.x)**2 \
                                             + (veh[i].position.y - requests[req_index].source.y)**2)\
                    + np.sqrt((requests[req_index].source.x-requests[req_index].destination.x)**2 +\
                              (requests[req_index].source.y-requests[req_index].destination.y)**2)
                    
                    if added_distance > veh[i].distance_left \
                    or requests[req_index].weight > veh[i].max_payload \
                    or requests[req_index].volume > veh[i].max_volume:
                        return 1e100 # Max value for non compatible allocation
                    
                    total_time[i] += added_distance/veh[i].speed + veh[i].set_up_time \
                    + veh[i].drop_off_time
                    veh[i].distance_left -= added_distance
                    veh[i].position = requests[req_index].destination

        return veh, np.max(total_time)

def concatenate(vec1, vec2):
    if len(vec1) != len(vec2):
        print("ERROR!!!")
        return
    
    vector = []
    
    for i in range(len(vec1)):
        vector.append(vec1[i]+vec2[i])
    return vector


def Allocation(boxes, items):
    vector = []
    
    if boxes == 2:
        for i in range(items+1):
            vector.append([items-i, i])
            
    else:
        for i in range(items+1):
            solution = Allocation(boxes-1, i)
            init = []
            for j in range(len(solution)):
                init.append([items - i])
            concat = concatenate(init, solution)
            for elem in concat:
                vector.append(elem)
    
    return vector


def getAllActions(vehicles, requests):
    
    num_veh = len(vehicles)
    num_req = len(requests)
    
    allocations      = Allocation(num_veh, num_req)
    req_permutations = list(permutations(range(1, num_req+1)))
    
    actions = np.zeros((len(allocations)*len(req_permutations), num_veh*num_req))
    for i, allocation in enumerate(allocations):
        for j, req_permutation in enumerate(req_permutations):
            index = 0
            for k, reqs in enumerate(allocation):
                actions[i*len(req_permutations)+j][k*num_req:k*num_req+reqs] = req_permutation[index:index+reqs]
                index += reqs
    
    scores = [get_score(action, vehicles, requests) for action in actions]
    
    vehicles = [scores[i][0] for i in range(len(scores))]
    costs    = [scores[i][1] for i in range(len(scores))]
    
    return actions, vehicles, costs

"""
req_1 = plannerFull.Request(plannerFull.Position(-3, 3),plannerFull.Position(-1, 2),0,plannerFull.Volume(0,0,0))
req_2 = plannerFull.Request(plannerFull.Position( 0, 3),plannerFull.Position( 2, 2),0,plannerFull.Volume(0,0,0))
req_3 = plannerFull.Request(plannerFull.Position( 2,-1),plannerFull.Position(-1,-2),0,plannerFull.Volume(0,0,0))
request_buffer = [req_1, req_2, req_3]

drone_1 = plannerFull.Drone('a',plannerFull.Position(-3, 2),100,plannerFull.Volume(10,10,10),100000,2,3,2)
drone_2 = plannerFull.Drone('b',plannerFull.Position( 3,-2),100,plannerFull.Volume(10,10,10),100000,2,3,2)
drones_available = [drone_1, drone_2]

result = getAllActions(drones_available, request_buffer)

for res in result:
    print(res[2])
    
"""