from os import chdir
chdir("/home/bernardo/Research Project/PlanningCustodian_3")
import json
import planner
import numpy as np
import time

from web3 import Web3

truffle_url = "HTTP://127.0.0.1:9545"

web3 = Web3(Web3.HTTPProvider(truffle_url))

compiled_custodian_path = 'build/contracts/Custodian.json'
compiled_vehicle_path = 'build/contracts/VehicleOracle.json'
compiled_request_path = 'build/contracts/RequestOracle.json'

deployed_custodian_address = '0x4d1E917A6049bb14164c35c04433D0d91BE4E74b'
deployed_vehicle_address = '0x55C311eE010CcD9E4190080F01F12Decc82E84A9'
deployed_request_address = '0x25DCD9C3843452Ae882eF54e795D0F78F0B99360'

with open(compiled_custodian_path) as file:
    custodian_json = json.load(file)
    custodian_abi  = custodian_json['abi']

custodian = web3.eth.contract(address=deployed_custodian_address, abi=custodian_abi)

with open(compiled_vehicle_path) as file:
    vehicle_json = json.load(file)
    vehicle_abi  = vehicle_json['abi']

vehicle = web3.eth.contract(address=deployed_vehicle_address, abi=vehicle_abi)

with open(compiled_request_path) as file:
    request_json = json.load(file)
    request_abi  = request_json['abi']

request = web3.eth.contract(address=deployed_request_address, abi=request_abi)

web3.eth.defaultAccount = web3.eth.accounts[0]

tx_hash = request.functions.setNewSource(web3.eth.accounts[0]).transact()
web3.eth.waitForTransactionReceipt(tx_hash)
tx_hash = custodian.functions.setReqCon(deployed_request_address).transact()
web3.eth.waitForTransactionReceipt(tx_hash)

req_1 = planner.Request(planner.Position(-3, 3),planner.Position(-1, 2),0,planner.Volume(0,0,0))
req_2 = planner.Request(planner.Position( 0, 3),planner.Position( 2, 2),0,planner.Volume(0,0,0))
req_3 = planner.Request(planner.Position( 2,-1),planner.Position(-1,-2),0,planner.Volume(0,0,0))
request_buffer = [req_1, req_2, req_3]

drone_1 = planner.Drone('a',planner.Position(-3, 2),100,planner.Volume(10,10,10),100000,2,3,2)
drone_2 = planner.Drone('b',planner.Position( 3,-2),100,planner.Volume(10,10,10),100000,2,3,2)
drones_available = [drone_1, drone_2]

ratio = request.functions.getFeeDistanceRatio().call()

for req in request_buffer:
    value = int(ratio * np.ceil(np.sqrt((req.source.x - req.destination.x)**2 + (req.source.y - req.destination.y)**2)))
    tx_hash = request.functions.newRequest(req.source.x, req.source.y,
                                            req.destination.x, req.destination.y,
                                            req.weight,
                                            req.volume.length, req.volume.width, req.volume.height).transact({'value': value})
    web3.eth.waitForTransactionReceipt(tx_hash)


i = 1
for drone in drones_available:
    web3.eth.defaultAccount = web3.eth.accounts[0]
    tx_hash = vehicle.functions.addKnownVehicle(web3.eth.accounts[i]).transact()
    web3.eth.waitForTransactionReceipt(tx_hash)
    time.sleep(5)
    web3.eth.defaultAccount = web3.eth.accounts[i]
    #tx_hash = vehicle.functions.isAvailable(True).transact()
    #web3.eth.waitForTransactionReceipt(tx_hash)
    tx_hash = vehicle.functions.setVehicleProperties(drone.position.x, drone.position.y,
                                                      drone.max_payload,
                                                      drone.max_volume.length, drone.max_volume.width, drone.max_volume.height,
                                                      drone.distance_left,
                                                      drone.speed,
                                                      drone.set_up_time,
                                                      drone.drop_off_time,
                                                      drone.time_for_task).transact()
    web3.eth.waitForTransactionReceipt(tx_hash)
    i += 1
    
web3.eth.defaultAccount = web3.eth.accounts[0]
seeds = []
for i in [3, 4, 5, 6]:
    tx_hash = custodian.functions.addVoter(web3.eth.accounts[i]).transact()
    web3.eth.waitForTransactionReceipt(tx_hash)
    tx_hash = custodian.functions.enableVoter().transact({'from':web3.eth.accounts[i],'value': web3.toWei(1,'ether')})
filter_seed=custodian.events.newVoterSeed.createFilter(fromBlock=0, toBlock='latest')
eventlist = filter_seed.get_all_entries()
for i in [3, 4, 5, 6]:
    seeds.append(eventlist[i-3]['args']['seed'])
#%%
 
#tx_hash = contract.functions.unsafeFirstCycle().transact()
for i in [3, 4, 5, 6]:
    web3.eth.defaultAccount = web3.eth.accounts[i]
    np.random.seed(seeds[i-3])
    root_f = planner.computeAllocation(request_buffer, drones_available, 20, 4)
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
    old_bal = web3.eth.getBalance(web3.eth.accounts[i])
    tx_hash = custodian.functions.acceptVote(int(np.min(action_scores)),
                                            solution).transact()
    web3.eth.waitForTransactionReceipt(tx_hash)
    new_bal = web3.eth.getBalance(web3.eth.accounts[i])
    print('------N',i,'------')
    print(solution)
    print(int(np.min(action_scores)))
    print('The cost of transaction was:',(old_bal-new_bal)/1e18,'ETH')

winning_gene = custodian.functions.getLastVoting().call()
print('The winning gene is:')
print(winning_gene)

tx_hash = custodian.functions.raiseDispute(0).transact({'from':web3.eth.accounts[3], 'value': 4*10**6})
web3.eth.waitForTransactionReceipt(tx_hash)

initial_block = 0
eventlist = []
filter_disputeRaised=custodian.events.DisputeRaised.createFilter(fromBlock=initial_block, toBlock='latest')
# To be put in an infinite loop
while len(eventlist) == 0:
    eventlist = filter_disputeRaised.get_all_entries()
    if len(eventlist) > 0:
        initial_block = eventlist[0]['blockNumber']
        myfilter_new=custodian.events.DisputeRaised.createFilter(fromBlock=initial_block, toBlock='latest')
print(eventlist[0]['args'])

for i in [3, 4, 5, 6]:
    if(web3.eth.accounts[i] == eventlist[0]['args']['disputer'] or web3.eth.accounts[i] == winning_gene[0]):
        continue
    tx_hash = custodian.functions.acceptDisputeVote(0, False).transact({'from':web3.eth.accounts[i]})
    web3.eth.waitForTransactionReceipt(tx_hash)
   
filter_disputeRaised=custodian.events.DisputeEnded.createFilter(fromBlock=0, toBlock='latest')
eventlist = filter_disputeRaised.get_all_entries()
print(eventlist[0]['args']['won'])
print(custodian.functions.allowedVoters(winning_gene[0]).call())

""" COST ANALYSIS

Cost of deployment 0.07001582 ETH
Cost of voting with 3: 0.00065.... ETH with (1) 0.000348648 and (1) 0.000438648 ETH for the other votes
Cost of voting with 4: 0.000697754 ETH with (2) 0.000348648 and (1) 0.000438648 ETH for the other votes
Cost of voting with 5: ERROR :(

"""
#transact({'from':'you account address','value': web3.toWei(2,'ether')})

#myfilter = mycontract.eventFilter('EventName', {'fromBlock': 0,'toBlock': 'latest'});
#eventlist = myfilter.get_all_entries()
# %%