from os import chdir
chdir("/home/bernardo/Research Project/PlanningCustodian_3/Simulation")
import json
import planner
import numpy as np
from time import sleep
import threading
from drone import Drone, move
from voter import vote
from collections import namedtuple
from source import source

from web3 import Web3

Position = namedtuple(
    "Position", ("x", "y")
)
Volume = namedtuple(
    "Volume", ("length","width","height")
)

map_size = [-1000,1000,-1000,1000] # x_min, x_max, y_min, y_max

truffle_url = "HTTP://127.0.0.1:9545"

def computeFullBalance(web3,accounts):
    balance = 0
    for account in accounts:
        balance += web3.eth.getBalance(account)
    return balance

def main(number_of_drones, number_of_voters):
    web3 = Web3(Web3.HTTPProvider(truffle_url))
    
    accounts = web3.eth.accounts
    
    compiled_custodian_path = 'build/contracts/Custodian.json'
    compiled_vehicle_path = 'build/contracts/VehicleOracle.json'
    compiled_request_path = 'build/contracts/RequestOracle.json'
    
    with open(compiled_custodian_path) as file:
        custodian_json = json.load(file)
        custodian_abi  = custodian_json['abi']
        custodian_byte = custodian_json['bytecode']
        
    with open(compiled_vehicle_path) as file:
        vehicle_json = json.load(file)
        vehicle_abi  = vehicle_json['abi']
        vehicle_byte = vehicle_json['bytecode']
        
    with open(compiled_request_path) as file:
        request_json = json.load(file)
        request_abi  = request_json['abi']
        request_byte = request_json['bytecode']
        
    Custodian = web3.eth.contract(abi=custodian_abi,bytecode=custodian_byte)
    Vehicle   = web3.eth.contract(abi=vehicle_abi,bytecode=vehicle_byte)
    Request   = web3.eth.contract(abi=request_abi,bytecode=request_byte)
    
    tx_hash = Custodian.constructor().transact({'from':web3.eth.accounts[0]})
    # wait for mining
    trans_receipt = web3.eth.getTransactionReceipt(tx_hash)
    # get the contract address
    custodian_address = trans_receipt['contractAddress']
    # now we can instantiate the contract factory to get an instance of the contract.
    custodian = Custodian(custodian_address)
    
    tx_hash = Vehicle.constructor(custodian_address).transact({'from':web3.eth.accounts[0]})
    # wait for mining
    trans_receipt = web3.eth.getTransactionReceipt(tx_hash)
    # get the contract address
    vehicle_address = trans_receipt['contractAddress']
    # now we can instantiate the contract factory to get an instance of the contract.
    vehicle = Vehicle(vehicle_address)
    
    tx_hash = Request.constructor(custodian_address).transact({'from':web3.eth.accounts[0]})
    # wait for mining
    trans_receipt = web3.eth.getTransactionReceipt(tx_hash)
    # get the contract address
    request_address = trans_receipt['contractAddress']
    # now we can instantiate the contract factory to get an instance of the contract.
    request = Request(request_address)
    
    # Custodian interfaces
    tx_hash = custodian.functions.setReqCon(request_address).transact({'from':accounts[0]})
    web3.eth.waitForTransactionReceipt(tx_hash)
    tx_hash = custodian.functions.setVehCon(vehicle_address).transact({'from':accounts[0]})
    web3.eth.waitForTransactionReceipt(tx_hash)
    
    
    chdir("/home/bernardo/Research Project/PlanningCustodian_3/Simulation")
    # VEHICLES INITIALIZATION
    drones_accounts = accounts[1:number_of_drones+1]
    positions = [Position(np.random.randint(map_size[0],map_size[1]),np.random.randint(map_size[2],map_size[3])) for _ in range(number_of_drones)]
    max_volume = Volume(10,10,10)
    drones = []
    t_drones = []
    for i in range(number_of_drones):
        drones.append(Drone(positions[i], 10, max_volume, int(1e9), 5, 25, 30, drones_accounts[i], vehicle, request, custodian))
        # Add vehicle
        vehicle.functions.addKnownVehicle(drones_accounts[i]).transact({'from':accounts[0]})
        t_drones.append(threading.Thread(target=move, args=(drones[i], web3)))
        
    for t in t_drones:
        t.daemon = True
        t.start()
    
    # SOURCE INITIALIZATION
    tx_hash = request.functions.setNewSource(accounts[number_of_drones + 1]).transact({'from':accounts[0]})
    web3.eth.waitForTransactionReceipt(tx_hash)
    t_source = threading.Thread(target=source, args=(accounts[number_of_drones + 1], map_size, request, web3))
    t_source.daemon = True
    t_source.start()
    
    # VOTERS INITIALIZATION
    value = custodian.functions.initial_Deposit().call()
    voters_accounts = accounts[number_of_drones+2 : number_of_drones+number_of_voters+3]
    t_voters = []
    for i in range(number_of_voters):
        # Add voter
        tx_hash = custodian.functions.addVoter(voters_accounts[i]).transact({'from':accounts[0]})
        web3.eth.waitForTransactionReceipt(tx_hash)
        # Enable voter
        tx_hash = custodian.functions.enableVoter().transact({'from':voters_accounts[i], 'value':value})#web3.toWei(1,'ether')})
        web3.eth.waitForTransactionReceipt(tx_hash)
        t_voters.append(threading.Thread(target=vote, args=(voters_accounts[i], map_size, custodian, request, vehicle, 30, 20, 4, web3)))
        
    for t in t_voters:
        t.daemon = True
        t.start()
    
    balance = computeFullBalance(web3,accounts)
    sleep(30)
    custodian.functions.unsafeFirstCycle().transact({'from':accounts[0]})
    # PRINT THE BLOCKCHAIN EVENTS' EVOLUTION
    counter_VoteCampFinished = 0
    counter_disputeRaised = 0
    counter_disputeEnded = 0
    filter_VoteCampFinished=custodian.events.VoteCampFinished.createFilter(fromBlock=0, toBlock='latest')
    filter_disputeRaised=custodian.events.DisputeRaised.createFilter(fromBlock=0, toBlock='latest')
    filter_disputeEnded=custodian.events.DisputeEnded.createFilter(fromBlock=0, toBlock='latest')
    while True:
        event_VoteCampFinished = filter_VoteCampFinished.get_all_entries()
        if len(event_VoteCampFinished) > counter_VoteCampFinished:
            print('-----------WINNER------------')
            for i in range(len(event_VoteCampFinished) - counter_VoteCampFinished-1,len(event_VoteCampFinished)):
                print(event_VoteCampFinished[i]['args'])
            counter_VoteCampFinished = len(event_VoteCampFinished)
        
        event_disputeRaised = filter_disputeRaised.get_all_entries()
        if len(event_disputeRaised) > counter_disputeRaised:
            print('-----------DISPUTE------------')
            for i in range(len(event_disputeRaised) - counter_disputeRaised-1,len(event_disputeRaised)):
                print(event_disputeRaised[i]['args'])
            counter_disputeRaised = len(event_disputeRaised)
        
        event_disputeEnded = filter_disputeEnded.get_all_entries()
        if len(event_disputeEnded) > counter_disputeEnded:
            print('-----------DISPUTE SOLVED------------')
            for i in range(len(event_disputeEnded) - counter_disputeEnded-1,len(event_disputeEnded)):
                print(event_disputeEnded[i]['args'])
            counter_disputeEnded = len(event_disputeEnded)
        
        new_balance = computeFullBalance(web3,accounts)
        cost = (balance - new_balance) / 10**18
        print(cost,'ether were spent')
        balance = new_balance
        sleep(10)
        
        
if __name__ == "__main__":
    chdir("/home/bernardo/Research Project/PlanningCustodian_3")
    number_of_drones = 3
    number_of_voters = 4
    #simulation_ratio = 5
    main(number_of_drones, number_of_voters)