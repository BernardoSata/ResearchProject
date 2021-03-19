import numpy as np
import copy
from time import time

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
        future_tuples = [(1,.1),(2,.2),(3,.3),(4,.2)]
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

    def ucb_score(self, scale=10, max_value=1e100):

        if self.times_visited == 0:
            return max_value

        U = np.sqrt(2*np.log(self.parent.times_visited)/self.times_visited)

        return self.value - scale*U                                           # Minus for minimization
    
    def action_score(self, scale=10, max_value=1e100):
        
        if self.actions == []:
            return None
        
        gamma = 0.9
        
        action_scores = np.zeros((len(self.children_lists),1))
        index = 0
        for children_list in self.children_lists:
            if len(children_list[0][0].actions) == 0:                         # Family not explored yet
                action_scores[index] = - 1e100
            else:
                prob = []
                values = []
                for child in children_list:
                    prob.append(child[1])
                    values.append(child[0].value)
                action_scores[index] = np.sum(np.asarray(prob)*(np.asarray(self.actions[index][2]) + gamma *np.asarray(values)))\
                / np.sum(prob) - \
                np.sqrt(2*np.log(self.times_visited)/children_list[index][0].times_visited) 
            index += 1
        return action_scores

    # MCTS steps

    def select_best_action(self):
        """
        Picks the leaf with highest priority to expand
        Does so by recursively picking nodes with best UCB-1 score until it reaches the leaf.
        """
        #print('selection')
        best_arg = np.argmin(self.action_score())
        best_children = self.children_lists[best_arg]               # Selects the most promising nodes
        
        if len(best_children[0][0].actions) == 0:                   # If family was not yet explored
            nodes = []
            for child in best_children:
                nodes.append(child[0])
            return nodes
        
        prob = []
        for child in best_children:
            prob.append(child[1])
        sum_prob = np.cumsum(prob)
        index = 0
        rand = np.random.random() * sum_prob[-1]
        while rand > sum_prob[index]:                            # Select the next state based on its probability
            index += 1
        
        return best_children[index][0].select_best_action()

    
    def propagate(self, child_value):
        """
        #Uses child value (sum of rewards) to update parents recursively.
        """
        # compute node value
        my_value = self.immediate_reward + child_value

        # update value_sum and times_visited
        self.value_sum += my_value
        self.times_visited += 1

        # propagate upwards
        if not self.is_root():
            self.parent.propagate(my_value) 

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
    def __init__(self):
        self.requestsDistribution = RequestsDistribution()
    
    def expand_and_update(self, nodes_f, timeout, map_size):
        #print('Expanding')
        
        #drones_solution = []
    
        args = []
        len_n = len(nodes_f)

        for i in range(len_n):
            args.append((nodes_f[i].node.requests, nodes_f[i].node.drones, timeout))
        
        #start = time()
        output = [plan_GA(arg) for arg in args]
        #print(time()-start)

        actions = []
        for result in output:
            actions.append((result[0],result[1],result[2]))

        for i in range(len(actions)):
            self.add_children(nodes_f[i], actions[i][0], actions[i][1], actions[i][2], map_size)
            
        self.update_values(nodes_f)
        
    def add_children(self, parent, genes, drones, costs, map_size):
        depth = 0
        pointer = parent
        while pointer.parent != None:
            depth += 1
            pointer = pointer.parent

        new_requests, probabilityList = self.requestsDistribution.futureRequest(len(parent.node.requests), depth, map_size)
        
        for index in range(len(costs)):
            parent.children_lists.append([])
            for j in range(len(probabilityList)):
                node = Node(new_requests[j], drones[index])
                node_f = Node_f(parent, costs[index], node, probabilityList[j])
                parent.children_lists[index].append((node_f,probabilityList[j]))
            parent.actions.append((genes[index],drones[index],costs[index]))

    def update_values(self, nodes):
        #print('Updating')
        for node in nodes:
            costs = []
            for action in node.actions:
                costs.append(action[2])
            node.value = np.min(costs)         # Minimum among future action costs
            node.times_visited += 1
          
        gamma = 0.9
        pointer = nodes[0].parent
        while pointer != None:
            index = 0
            action_scores = np.zeros((len(pointer.children_lists),1))
            for children_list in pointer.children_lists:
                if len(children_list[0][0].actions) == 0:       # Family not explored yet (do not affect value computation)
                    action_scores[index] = 1e100
                else:
                    prob = []
                    values = []
                    for child in children_list:
                        prob.append(child[1])
                        values.append(child[0].value)
                    action_scores[index] = np.sum(np.asarray(prob) * np.asarray(np.asarray(pointer.actions[index][2]) + gamma*np.asarray(values)))\
                     / np.sum(prob)
                index += 1
                
            pointer.value = np.min(action_scores)
            pointer.times_visited += 1
            pointer = pointer.parent


class Env_GA:
    """Environment definition defines: available actions, costs ...""" 
    def __init__(self, request_buffer, drones_available):
        self.request_buffer = request_buffer
        self.drones_available = drones_available

    def get_score(self, allocation):
        total_time = np.zeros((len(self.drones_available),1))
        dr_av = copy.deepcopy(self.drones_available)
    
        for i in range(len(dr_av)):
            for j in range(len(self.request_buffer)):
                req_index = (int) (allocation[i * len(self.request_buffer) + j])
                if req_index != 0:
                    req_index -= 1
                    added_distance = np.sqrt((dr_av[i].position.x - self.request_buffer[req_index].source.x)**2 \
                                             + (dr_av[i].position.y - self.request_buffer[req_index].source.y)**2)\
                    + np.sqrt((self.request_buffer[req_index].source.x-self.request_buffer[req_index].destination.x)**2 +\
                              (self.request_buffer[req_index].source.y-self.request_buffer[req_index].destination.y)**2)
                    
                    if added_distance > dr_av[i].distance_left \
                    or self.request_buffer[req_index].weight > dr_av[i].max_payload \
                    or self.request_buffer[req_index].volume > dr_av[i].max_volume:
                        return 1e100 # Max value for non compatible allocation
                    
                    total_time[i] += added_distance/dr_av[i].speed + dr_av[i].set_up_time \
                    + dr_av[i].drop_off_time
                    dr_av[i].distance_left -= added_distance
                    dr_av[i].position = self.request_buffer[req_index].destination

        return np.max(total_time)

    def crossover(self, allocation1, allocation2):
        index = np.random.randint(len(allocation1)//5,len(allocation1)//2) # The first fifth to half is taken from parent1
        child = allocation1[0:index]
        all2 = copy.deepcopy(allocation2)
        for val in child:
            all2 = np.delete(all2, np.where(all2 == val)[0][0]) # Removes already used allocations
        child = np.concatenate((child,all2))
        
        return child
    
    def swap(self, allocation):
        new_alloc = copy.deepcopy(allocation)
        
        index1 = np.random.randint(0,len(allocation))
        index2 = np.random.randint(0,len(allocation))
        
        temp = allocation[index1]
        new_alloc[index1] = allocation[index2]
        new_alloc[index2] = temp
        
        return allocation
    
    def invert(self, allocation):
        
        if len(allocation == 2):
            temp = allocation[0]
            allocation[0] = allocation[1]
            allocation[1] = temp
            return allocation
        
        new_alloc = copy.deepcopy(allocation)
        
        index1 = np.random.randint(0,len(allocation)-2)
        index2 = np.random.randint(index1+1,len(allocation))
        
        for i in range((index2-index1)//2):
            temp = new_alloc[index1+i]
            new_alloc[index1+i] = new_alloc[index2-i]
            new_alloc[index2-i] = temp
            
        return new_alloc
    
    def select_elite(self, population, percentile):
        scores = [-self.get_score(element) for element in population] # The minus sign ease the process of minimizing time
        threshold = np.percentile(scores, percentile)
        #print('The top ',100-percentile,'% has at least ',threshold,' score')
        elite = [population[i] for i in range(len(population)) if scores[i] >= threshold]
        bottom = [population[i] for i in range(len(population)) if scores[i] < threshold]
        if len(elite) == 0 or len(bottom) == 0:
            elite = population
            bottom = population
        return elite, bottom, threshold
        
    def new_generation(self, population, prob_mutation, prob_elite):
        elite, bottom, threshold = self.select_elite(population,60) # Top 40%
        new_population = np.zeros(np.shape(population))
        for i in range(len(population)):
            if np.random.random_sample() < prob_elite:
                parent1 = elite[np.random.randint(0,len(elite))]
            else:
                parent1 = bottom[np.random.randint(0,len(bottom))]
            if np.random.random_sample() < prob_elite:
                parent2 = elite[np.random.randint(0,len(elite))]
            else:
                parent2 = bottom[np.random.randint(0,len(bottom))]
            new_child = self.crossover(parent1, parent2)
                        
            if np.random.random_sample() < prob_mutation: # A part of the population receives some random mutation
                if np.random.random_sample() < 1/2:
                    new_child = self.swap(new_child)
                else:
                    new_child = self.invert(new_child)
                    
            new_population[i] = new_child
        
        return new_population, threshold
    
    def update(self, allocation):
        dr_av = copy.deepcopy(self.drones_available)
    
        for i in range(len(dr_av)):
            for j in range(len(self.request_buffer)):
                req_index = (int) (allocation[i * len(self.request_buffer) + j])
                if req_index != 0:
                    req_index -= 1
                    added_distance = np.sqrt((dr_av[i].position.x - self.request_buffer[req_index].source.x)**2 \
                                             + (dr_av[i].position.y - self.request_buffer[req_index].source.y)**2)\
                    + np.sqrt((self.request_buffer[req_index].source.x-self.request_buffer[req_index].destination.x)**2 +\
                              (self.request_buffer[req_index].source.y-self.request_buffer[req_index].destination.y)**2)
                    
                    if added_distance > dr_av[i].distance_left \
                    or self.request_buffer[req_index].weight > dr_av[i].max_payload \
                    or self.request_buffer[req_index].volume > dr_av[i].max_volume:
                        return 1e100 # Max value for non compatible allocation
                    
                    dr_av[i].distance_left -= added_distance
                    dr_av[i].position = self.request_buffer[req_index].destination
        return dr_av

def plan_GA(input):
    # Drones and Requests building
    request_buffer, drones_available, timeout = input[:]
    
    if timeout == -1:
        return (None,None)

    env_GA = Env_GA(request_buffer, drones_available)

    # Population building
    size_gene = len(request_buffer)*len(drones_available)
    size_population = 50
    prob_mutation = 1/2
    prob_elite = 3/4
    
    population = np.zeros((size_population,size_gene))
    request_list = range(len(request_buffer))
    for i in range(size_population):
        for req in request_list:
            index = np.random.randint(0,size_gene)
            while population[i][index] != 0:
                index = np.random.randint(0,size_gene)
            population[i][index] = req+1
        
    # GA cycle
    start = time()
    while time() - start < timeout:
        population, _ = env_GA.new_generation(population, prob_mutation , prob_elite)
            
    best_genes = []
    best_scores = []
    final_drones = []
    scores = [env_GA.get_score(element) for element in population]
    old_score = 0
    i = 0
    discarded = 0
    while i < 4:
        best = np.argmin(scores)
        #if equal_genes(best_genes,population[best]): # We check if it's equal to the last added
        if old_score ==  scores[best]:
            scores[best] = 1e100
            if discarded < (size_population - 4):
                discarded += 1
            else:
                i += 1
            continue
        best_genes.append(population[best])
        best_scores.append(scores[best])
        final_drones.append(env_GA.update(population[best]))
        old_score = scores[best]
        scores[best] = 1e100                # So that the next highest is selected
        i += 1
    
    return (best_genes, final_drones, best_scores)

def computeAllocation(request_buffer, drones_available, max_time, timeout, map_size):

    env_f = Env_f()

    root = Node(request_buffer, drones_available)
    root_f = Node_f(None, 0, root, 1)

    start = time()

    genes, drones, costs = plan_GA((root.requests, root.drones, timeout))
    env_f.add_children(root_f, genes, drones, costs, map_size)

    while time() - start < max_time:
        nodes_f = root_f.select_best_action()
        env_f.expand_and_update(nodes_f, timeout, map_size)
        
    return root_f