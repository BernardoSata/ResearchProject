import numpy as np
from time import sleep
from planner import Request
from collections import namedtuple

Position = namedtuple(
    "Position", ("x", "y")
)
Volume = namedtuple(
    "Volume", ("length","width","height")
)

def source(address, map_size, requestCon, web3):
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
    
    feeDistanceRatio = requestCon.functions.getFeeDistanceRatio().call()
    
    while True:
        request = Request(Position(int(np.random.normal(xs_mean,xs_dev)),int(np.random.normal(ys_mean,ys_dev))), \
                          Position(int(np.random.normal(xd_mean,xd_dev)),int(np.random.normal(yd_mean,yd_dev))), \
                          int(np.random.normal(w_mean,w_dev)))
        
        value = int(feeDistanceRatio * np.ceil(np.sqrt((request.source.x - request.destination.x)**2 + (request.source.y - request.destination.y)**2)))
        
        tx_hash = requestCon.functions.newRequest(request.source.x, request.source.y,\
                                                  request.destination.x, request.destination.y,\
                                                  request.weight,\
                                                  request.volume.length, request.volume.height, request.volume.width).transact({'from':address,'value':value})
        print('Request sent: Source (',request.source.x,',',request.source.y,')','Destination (',request.destination.x,',',request.destination.x,')')
        web3.eth.waitForTransactionReceipt(tx_hash)
        next_time = np.random.gamma(k,theta)
        sleep(next_time)
        