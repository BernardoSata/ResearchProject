import numpy as np
from time import time
from actionProposal import getAllActions
import matplotlib.pyplot as plt

from collections import namedtuple

Position = namedtuple(
    "Position", ("x", "y")
)
Volume = namedtuple(
    "Volume", ("length","width","height")
)

class Request:
  """package delivery class"""
  source = Position(0,0)
  destination = Position(0,0)
  weight = 0
  volume = Volume(0,0,0)

  def __init__(self, source, destination, weight, volume=Volume(0,0,0)):
    self.source = source
    self.destination = destination
    self.weight = weight
    self.volume = volume

  def __eq__(self, other):
    try:
        return (self.source, self.destination, self.weight, self.volume) == (other.source, other.destination, other.weight, other.volume)
    except AttributeError:
        return NotImplemented
        
  def __repr__(self):
    return "<Request of source at: (%s,%s), destination at: (%s,%s)>" % (self.source.x, self.source.y,self.destination.x,self.destination.y)

  def __str__(self):
    return "From str method of Request of source at: (%s,%s), destination at: (%s,%s)>" % (self.source.x, self.source.y,self.destination.x,self.destination.y)

class Drone:
  """drone device definition"""
  position = Position(0,0)
  max_payload = 0
  max_volume = Volume(0,0,0)
  distance_left = 0
  # Averaged values
  speed = 0
  set_up_time = 0
  drop_off_time = 0
  time_for_task = 0

  def __init__(self, order, position, max_payload, max_volume, distance_left, speed, set_up_time, drop_off_time, time_for_task=0):
    self.order = order
    self.position = position
    self.max_payload = max_payload
    self.max_volume = max_volume
    self.distance_left = distance_left
    self.speed = speed
    self.set_up_time = set_up_time
    self.drop_off_time = drop_off_time
    self.time_for_task = time_for_task

  def __eq__(self, other):
    try:
        return self.order == other.order
    except AttributeError:
        return NotImplemented

  def __repr__(self):
    return "<Drone at: (%f,%f), distance left: %f, time to idleness: %f>" % (self.position.x, self.position.y,self.distance_left,self.time_for_task)

  def __str__(self):
    return "From str method of Drone at: (%f,%f), distance left: %f, time to idleness: %f>" % (self.position.x, self.position.y,self.distance_left,self.time_for_task)


class RequestsDistribution():
    def __init__(self):
      self.requestList = []
      self.probabilityList = []

    def futureRequest(self, num_requests, depth, map_size):
        if depth < len(self.requestList):
            return self.requestList[depth], self.probabilityList[depth]
        
        # Call function to receive distributions (here constants)
        # Standard gamma distribution for time (mean=k*theta, var=k*theta^2)
        # Mean: 12.9 min
        k     = 10.1
        theta = 1.33
        # Distribution of weights of packages
        w_mean = 5
        w_dev  = 0
        # Distribution in city location
        # source
        xs_mean = int((map_size[0] + map_size[1]) / 2)
        xs_dev  = int((map_size[1] - map_size[0]) / 10)
        ys_mean = int((map_size[2] + map_size[3]) / 2)
        ys_dev  = int((map_size[3] - map_size[2]) / 10)
        # destination
        xd_mean = int((map_size[0] + map_size[1]) / 2)
        xd_dev  = int((map_size[1] - map_size[0]) / 10)
        yd_mean = int((map_size[2] + map_size[3]) / 2)
        yd_dev  = int((map_size[3] - map_size[2]) / 10)

        # Here it should compute the probability of new requests given the older ones (num_req, prob)
        #future_tuples = [(4,.1),(5,.2),(6,.3),(7,.2)]
        future_tuples = [(1,.1),(2,.2),(3,.3)]#,(4,.2)]
        new_requests = []
        
        for f_t in future_tuples:
            new_requests.append([Request(Position(np.random.normal(xs_mean,xs_dev),np.random.normal(ys_mean,ys_dev)), \
                                         Position(np.random.normal(xd_mean,xd_dev),np.random.normal(yd_mean,yd_dev)), \
                                         np.random.normal(w_mean,w_dev)) for _ in range(f_t[0])])
        probabilities = [f_t[1] for f_t in future_tuples]

        self.requestList.append(new_requests)
        self.probabilityList.append(probabilities)

        return new_requests, probabilities
    

class Node:

    # metadata:
    parent = None  # parent Node
    value = 0.  # sum of state values from all visits (numerator)
    #times_visited = 0  # counter of visits (denominator)
    node = None

    def __init__(self, parent, requests, drones, probability):
        """Creates and empty node with no children.
        Does so by commiting an action and recording outcome."""

        self.parent = parent
        self.actions = []             # List of (genes, drones, costs) tuples
        self.children_lists = []      # List of lists of (new_node,probabilities) tuples
        self.requests = requests
        self.drones = drones
        self.probability = probability

    def is_leaf(self):
        return len(self.actions) == 0

    def is_root(self):
        return self.parent is None
    
    def action_score(self):
        
        if self.actions == []:
            return None
        
        action_scores = np.zeros((len(self.children_lists),1))
        index = 0
        for children_list in self.children_lists:
            prob = []
            values = []
            for child in children_list:
                prob.append(child[1])
                values.append(child[0].value)
            action_scores[index] = np.sum(np.asarray(prob)*(np.asarray(self.actions[index][2]) + np.asarray(values))) / np.sum(prob)
            index += 1

        return action_scores


    def select_best_action(self):
        """
        Picks the leaf with highest priority to expand
        Does so by recursively picking nodes with best UCB-1 score until it reaches the leaf.
        """
        #print('selection')
        eps = 0.3
        rand = np.random.random()
        if rand > eps:
            best_arg = np.random.randint(0,len(self.actions))
        else:
            best_arg = np.argmin(self.action_score())
        best_children = self.children_lists[best_arg]            # Selects the most promising action
        
        prob = []
        for child in best_children:
            prob.append(child[1])
        sum_prob = np.cumsum(prob)
        index = 0
        rand = np.random.random() * sum_prob[-1]
        while rand > sum_prob[index]:                            # Sample the next state based on its probability
            index += 1
            
        if len(best_children[index][0].actions) == 0:            # If family was not yet explored
            return best_children[index][0]
        else:
            return best_children[index][0].select_best_action()


    def safe_delete(self):
        """safe delete to prevent memory leak in some python versions"""
        del self.parent
        for children_list in self.children_lists:
            for child in children_list:
                child[0].safe_delete()
                del child
        

class Env_f():
    """Environment needed to manage allocations"""
    def __init__(self, requestsDistribution):
        self.requestsDistribution = requestsDistribution
        
    def heuristic(self, node, depth):
        max_distance = 0
        for request in node.requests:
            distance = np.sqrt((request.destination.x-request.source.x)**2+(request.destination.y-request.source.y)**2)
            if distance > max_distance:
                max_distance = distance
        
        min_time = max_distance/node.drones[0].speed + node.drones[0].set_up_time + node.drones[0].drop_off_time
        for drone in node.drones[1:]:
            time = max_distance/drone.speed + drone.set_up_time + drone.drop_off_time
            if time < min_time:
                min_time = time
                
        #min_time *= depth
        
        return min_time
    
    def expand_and_update(self, node, map_size):
        #print('Expanding')
        
        depth = 0
        pointer = node
        while pointer.parent != None:
            depth += 1
            pointer = pointer.parent
       
        if depth > 3:
            return
        if depth == 3:
            _, _, costs = getAllActions(node.drones, node.requests)
            self.value = min(costs)
            self.update_values(node.parent)
            return
        else:
            genes, drones, costs = getAllActions(node.drones, node.requests)
            self.add_children(node, genes, drones, costs, map_size)
            new_node = node.select_best_action()
            self.expand_and_update(new_node, map_size)
            return
        
    def add_children(self, parent, genes, drones, costs, map_size):
        depth = 0
        pointer = parent
        while pointer.parent != None:
            depth += 1
            pointer = pointer.parent

        new_requests, probabilityList = self.requestsDistribution.futureRequest(len(parent.requests), depth, map_size)
        
        for index in range(len(costs)):
            parent.children_lists.append([])
            for j in range(len(probabilityList)):
                node = Node(parent, new_requests[j], drones[index], probabilityList[j])
                node.value = self.heuristic(node, depth)
                parent.children_lists[index].append((node,probabilityList[j]))
            parent.actions.append((genes[index],drones[index],costs[index]))
            

    def update_values(self, parent):
        #print('Updating')
        
        pointer = parent
        while pointer != None:
            index = 0
            action_scores = np.zeros((len(pointer.children_lists),1))
            for children_list in pointer.children_lists:
                prob = []
                values = []
                for child in children_list:
                    prob.append(child[1])
                    values.append(child[0].value)
                action_scores[index] = np.sum(np.asarray(prob) * np.asarray(np.asarray(pointer.actions[index][2]) + np.asarray(values)))\
                 / np.sum(prob)
                index += 1
                
            pointer.value = np.min(action_scores)
            #pointer.times_visited += 1
            pointer = pointer.parent



def computeAllocation(request_buffer, drones_available, max_time, map_size):

    requestsDistribution = RequestsDistribution()
    env_f = Env_f(requestsDistribution)

    root = Node(None, request_buffer, drones_available, 1)
    np.seterr('raise')

    start = time()
    
    genes, drones, costs = getAllActions(root.drones, root.requests)
    env_f.add_children(root, genes, drones, costs, map_size)
    env_f.update_values(root)
    old_value = root.value
    conv = 0
    values = []

    while time() - start < max_time:
        node = root.select_best_action()
        env_f.expand_and_update(node, map_size)
        values.append(old_value)
        new_value = root.value
        if abs(new_value - old_value) < old_value/500:
            conv += 1
        else:
            conv = 0
        #if conv == 200:
        #    break
        #else:
        old_value = new_value
            
    plt.plot(values)
        
    return root