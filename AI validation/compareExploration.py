import plannerFull
import plannerGreedy
from time import time
from actionProposal import getAllActions
import matplotlib.pyplot as plt


def computeAllocation(request_buffer, drones_available, max_time, map_size):

    requestsDistribution = plannerFull.RequestsDistribution()
    env_f = plannerFull.Env_f(requestsDistribution)
    env_g = plannerGreedy.Env_f(requestsDistribution)
    
    # FULL TREE EXPLORATION
    start = time()
    
    root = plannerFull.Node(request_buffer, drones_available)
    root_f = plannerFull.Node_f(None, 0, root, 1)
    
    root_f.explore(env_f, map_size, 0)
    
    print('The full tree took',time() - start,'seconds to complete')
    
    # GREEDY TREE EXPLORATION
    root_g = plannerGreedy.Node(None, request_buffer, drones_available, 1)

    start = time()
    
    genes, drones, costs = getAllActions(root_g.drones, root_g.requests)
    env_g.add_children(root_g, genes, drones, costs, map_size)
    env_g.update_values(root_g)
    old_value = root_g.value
    conv = 0
    values = []

    while time() - start < max_time:
        node_g = root_g.select_best_action()
        env_g.expand_and_update(node_g, map_size)
        values.append(old_value)
        new_value = root_g.value
        if abs(new_value - old_value) < old_value/500:
            conv += 1
        else:
            conv = 0
        if conv == 100:
            break
        else:
            old_value = new_value

    print('The greedy tree took',time() - start,'seconds to complete')        
    plt.plot(values)
    
    print('The full tree has a root value of',root_f.value)
    print('The greedy tree has a root value of',root_g.value)
        
    return root_f, root_g