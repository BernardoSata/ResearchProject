// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;

import * as P from "./PlanningLib.sol";

contract CustodianInt {
    function OpenedSeq() public view returns (uint256) {}
}

contract VehicleOracle {

    uint public feeDistanceRatio = 5;                      // To be tuned according to the distance scale (m, dm, cm...)
    uint public sequence = 1;

    address public owner = msg.sender;
    address payable public custodian;

    mapping(address => bool) public vehiclesKnown;
    mapping(uint => address[]) vehiclesAddresses;

    mapping(uint => mapping (address => P.Planning.Vehicle)) vehicles;

    CustodianInt custOr;

    constructor (address payable _conAdd) public {
        custodian = _conAdd;
        custOr = CustodianInt(_conAdd);
    }

    modifier restricted() {
        require(msg.sender == owner,
        "This function is restricted to the contract's owner");
        _;
    }
    /*
    function update() private {
        uint _seq = custOr.OpenedSeq() + 1;
        if(_seq != sequence) {
            vehiclesAddresses[sequence+1] = vehiclesAddresses[sequence];
            for(uint i=0; i<vehiclesAddresses[sequence+1].length; i++) {
                vehicles[sequence+1][vehiclesAddresses[sequence][i]] = vehicles[sequence][vehiclesAddresses[sequence][i]];
            }
            sequence = _seq;
        }
    }*/

    function update() public {
        require(msg.sender == custodian,"Only the custodian can reach this function");
        vehiclesAddresses[sequence+1] = vehiclesAddresses[sequence];
        for(uint i=0; i<vehiclesAddresses[sequence+1].length; i++) {
            vehicles[sequence+1][vehiclesAddresses[sequence][i]] = vehicles[sequence][vehiclesAddresses[sequence][i]];
        }
        sequence ++;
    }

    modifier isKnown() {
        require(vehiclesKnown[msg.sender]==true,"The vehicle is not known");
        _;
    }

    function sqrt(uint x) public pure returns (uint y) {
        uint z = (x + 1) / 2;
        y = x;
        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }
    }

    function setContractAddress(address _conAdd) public restricted {
        custOr = CustodianInt(_conAdd);
    }

    function addKnownVehicle(address _vehicle) public restricted {
        //update();
        if(vehiclesKnown[_vehicle] != true) {
            vehiclesKnown[_vehicle] = true;
            vehiclesAddresses[sequence].push(_vehicle);
        }
    }

    function removeKnownVehicle(address _vehicle) public restricted {
        //update();
        if(vehiclesKnown[_vehicle] == true) {
            vehiclesKnown[_vehicle] = false;
            for(uint i=0; i<vehiclesAddresses[sequence].length; i++) {
                if(vehiclesAddresses[sequence][i] == _vehicle) {
                    vehiclesAddresses[sequence][i] = vehiclesAddresses[sequence][vehiclesAddresses[sequence].length - 1];
                    delete(vehiclesAddresses[sequence][vehiclesAddresses[sequence].length - 1]);
                    //vehiclesAddresses[sequence].length --;
                    break;
                }
            }
        }
    }


    function setVehicleProperties(int _positionX, int _positionY,
                                  uint _maxPayload,
                                  uint _maxVolumeX, uint _maxVolumeY, uint _maxVolumeZ,
                                  uint _distanceLeft,
                                  uint _speed,
                                  uint _setUpTime,
                                  uint _dropOffTime,
                                  uint _timeForTask) public isKnown {

        //update();

        vehicles[sequence][msg.sender] = P.Planning.Vehicle(P.Planning.Position(_positionX,_positionY),
                                                                      _maxPayload,
                                                                      P.Planning.Volume(_maxVolumeX,_maxVolumeY,_maxVolumeZ),
                                                                      _distanceLeft,
                                                                      _speed,
                                                                      _setUpTime,
                                                                      _dropOffTime,
                                                                      _timeForTask);
    }

    function updateVehicleProperties(int _positionX, int _positionY, uint _distanceLeft, uint _timeForTask) public isKnown {

        //update();
    
    	// To be added in further development
    	// Check if the vehicle has actually completed the task with a QR proof
    	
    	uint distance = sqrt((uint(_positionX - vehicles[sequence][msg.sender].position.x))**2 +
                             (uint(_positionY - vehicles[sequence][msg.sender].position.y))**2);
                             
        //msg.sender.transfer(distance * feeDistanceRatio);
        (bool success, ) = msg.sender.call.value(distance * feeDistanceRatio)("");
        require(success, "Transfer failed.");

        vehicles[sequence][msg.sender].position.x    = _positionX;
        vehicles[sequence][msg.sender].position.y    = _positionY;
        vehicles[sequence][msg.sender].distance_left = _distanceLeft;
        vehicles[sequence][msg.sender].time_for_task = _timeForTask;

    }

    function getVehicles_1(uint _seq) public view returns(int[] memory _positionX,
                                                          int[] memory _positionY,
                                                          uint[] memory _maxPayload,
                                                          uint[] memory _volumeX,
                                                          uint[] memory _volumeY,
                                                          uint[] memory _volumeZ) {

        uint _len = vehiclesAddresses[_seq].length;
        address[] memory _addresses = vehiclesAddresses[_seq];

        _positionX      = new  int[](_len);
        _positionY      = new  int[](_len);
        _maxPayload     = new uint[](_len);
        _volumeX        = new uint[](_len);
        _volumeY        = new uint[](_len);
        _volumeZ        = new uint[](_len);
        
        for(uint i=0; i < _len; i++) {
            _positionX[i]    = vehicles[_seq][_addresses[i]].position.x;
            _positionY[i]    = vehicles[_seq][_addresses[i]].position.y;
            _maxPayload[i]   = vehicles[_seq][_addresses[i]].max_payload;
            _volumeX[i]      = vehicles[_seq][_addresses[i]].max_volume.len;
            _volumeY[i]      = vehicles[_seq][_addresses[i]].max_volume.height;
            _volumeZ[i]      = vehicles[_seq][_addresses[i]].max_volume.depth;
        }

    }

    function getVehicles_2(uint _seq) public view returns(uint[] memory _distanceLeft,
                                                          uint[] memory _speed,
                                                          uint[] memory _setUpTime,
                                                          uint[] memory _dropOffTime,
                                                          uint[] memory _timeForTask) {

        uint _len = vehiclesAddresses[_seq].length;
        address[] memory _addresses = vehiclesAddresses[_seq];

        _distanceLeft   = new uint[](_len);
        _speed          = new uint[](_len);
        _setUpTime      = new uint[](_len);
        _dropOffTime    = new uint[](_len);
        _timeForTask    = new uint[](_len);
        
        for(uint i=0; i < _len; i++) {
            _distanceLeft[i] = vehicles[_seq][_addresses[i]].distance_left;
            _speed[i]        = vehicles[_seq][_addresses[i]].speed;
            _setUpTime[i]    = vehicles[_seq][_addresses[i]].set_up_time;
            _dropOffTime[i]  = vehicles[_seq][_addresses[i]].drop_off_time;
            _timeForTask[i]  = vehicles[_seq][_addresses[i]].time_for_task;
        }

    }

    function getVehiclesAddresses(uint _seq) public view returns(address[] memory) {
        return vehiclesAddresses[_seq];
    }

    function getVehiclesNumber(uint _seq) public view returns(uint) {
        return vehiclesAddresses[_seq].length;
    }

    function returnFunds(uint _funds) public {
        require(msg.sender == custodian, "Only the Custodian Smart Contract can retrieve funds");
        (bool success, ) = custodian.call.value(_funds)("");
        require(success, "Transfer failed.");
    }

    receive() external payable {}
    fallback() external payable {}
}