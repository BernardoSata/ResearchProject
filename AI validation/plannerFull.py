import numpy as np
import copy
from time import time
from actionProposal import getAllActions

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
        future_tuples = [(2,.2),(3,.3)]
        new_requests = []
        
        for f_t in future_tuples:
            new_requests.append([Request(Position(np.random.normal(xs_mean,xs_dev),np.random.normal(ys_mean,ys_dev)), \
                                         Position(np.random.normal(xd_mean,xd_dev),np.random.normal(yd_mean,yd_dev)), \
                                         np.random.normal(w_mean,w_dev)) for _ in range(f_t[0])])
        probabilities = [f_t[1] for f_t in future_tuples]

        self.requestList.append(new_requests)
        self.probabilityList.append(probabilities)

        return new_requests, probabilities
    
Node = namedtuple(
    "Node", ("requests", "drones")
)

class Node_f:

    # metadata:
    parent = None  # parent Node
    value = 0.  # sum of state values from all visits (numerator)
    times_visited = 0  # counter of visits (denominator)
    node = None

    def __init__(self, parent, cost, node, probability):
        """Creates and empty node with no children.
        Does so by commiting an action and recording outcome."""

        self.parent = parent
        self.actions = []             # List of (genes, drones, costs) tuples
        self.children_lists = []      # List of lists of (new_node,probabilities) tuples
        self.node = node
        self.cost = cost
        self.probability = probability

    def is_leaf(self):
        return len(self.actions) == 0

    def is_root(self):
        return self.parent is None
    
    def explore(self, env_f, map_size, depth):

        if depth < 3:
            genes, drones, costs = getAllActions(self.node.drones, self.node.requests)
            env_f.add_children(self, genes, drones, costs, depth, map_size)
            
            for children_list in self.children_lists:
                for child in children_list:
                    child[0].explore(env_f, map_size, depth+1)
                    
            env_f.update_value(self)
            
        else:
            _, _, costs = getAllActions(self.node.drones, self.node.requests)
            self.value = np.min(costs)

    def safe_delete(self):
        """safe delete to prevent memory leak in some python versions"""
        del self.parent
        for children_list in self.children_lists:
            for child in children_list:
                child[0].safe_delete()
                del child
            
    def __str__(self):
        "parent",self.parent,"cost",self.cost,"node",self.node,"probability",self.probability
        

class Env_f():
    """Environment needed to manage allocations"""
    def __init__(self, requestsDistribution):
        self.requestsDistribution = requestsDistribution
   
    def add_children(self, parent, genes, drones, costs, depth, map_size):
        
        new_requests, probabilityList = self.requestsDistribution.futureRequest(len(parent.node.requests), depth, map_size)
        
        for index in range(len(costs)):
            parent.children_lists.append([])
            for j in range(len(probabilityList)):
                node = Node(new_requests[j], drones[index])
                node_f = Node_f(parent, costs[index], node, probabilityList[j])
                parent.children_lists[index].append((node_f,probabilityList[j]))
            parent.actions.append((genes[index],drones[index],costs[index]))

    def update_value(self, node):
        #print('Updating')
        """
        for node in nodes:
            costs = []
            for action in node.actions:
                costs.append(action[2])
            node.value = np.min(costs)         # Minimum among future action costs
            node.times_visited += 1
        """  
        gamma = 0.9
        index = 0
        action_scores = np.zeros((len(node.children_lists),1))
        for children_list in node.children_lists:
            #if len(children_list[0][0].actions) == 0:       # Family not explored yet (do not affect value computation)
            #    action_scores[index] = 1e100
            #else:
            prob = []
            values = []
            for child in children_list:
                prob.append(child[1])
                values.append(child[0].value)
            action_scores[index] = np.sum(np.asarray(prob) * np.asarray(np.asarray(node.actions[index][2]) + gamma*np.asarray(values)))\
             / np.sum(prob)
            index += 1
                
        node.value = np.min(action_scores)
        node.times_visited += 1



def computeAllocation(request_buffer, drones_available, map_size):

    requestsDistribution = RequestsDistribution()
    env_f = Env_f(requestsDistribution)

    root = Node(request_buffer, drones_available)
    root_f = Node_f(None, 0, root, 1)
    
    root_f.explore(env_f, map_size, 0)
        
    return root_f