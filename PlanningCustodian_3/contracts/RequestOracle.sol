// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;

import * as P from "./PlanningLib.sol";

contract CustodianInt {
    function OpenedSeq() public view returns (uint256) {}
}

contract RequestOracle {

    uint public feeDistanceRatio = 5;                      // To be tuned according to the distance scale (m, dm, cm...)
    uint256 public sequence;

    mapping(uint => P.Planning.Request[]) requests;

    address public source;
    address public owner = msg.sender;
    address payable public vehicle;

    CustodianInt custOr;

    constructor (address _conAdd) public {
        custOr = CustodianInt(_conAdd);
    }

    modifier onlySource() {
        require(msg.sender == source,
        "This function is restricted to the contract's source");
        _;
    }

    modifier restricted() {
        require(msg.sender == owner,
        "This function is restricted to the contract's owner");
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

    function update() private {
        sequence = custOr.OpenedSeq() + 1;
    }

    function setNewSource(address _newSource) public restricted {
        source = _newSource;
    }

    function setContractAddress(address _conAdd) public restricted {
        custOr = CustodianInt(_conAdd);
    }

    function setVehicleAddress(address payable _vehAdd) public {
        vehicle = _vehAdd;
    }

    function newRequest(int _sourceX, int _sourceY, int _destinationX, int _destinationY,
                        uint _weight, uint _volumeX, uint _volumeY, uint _volumeZ) public payable onlySource {

        update();

	    uint distance = sqrt((uint(_sourceX - _destinationX))**2 +
                             (uint(_sourceY - _destinationY))**2);
        require(msg.value >= distance * feeDistanceRatio, "Not enough money was sent for this request");
	
        requests[sequence].push(P.Planning.Request(P.Planning.Position(_sourceX, _sourceY),
                                                     P.Planning.Position(_destinationX, _destinationY),
                                                     _weight,
                                                     P.Planning.Volume(_volumeX, _volumeY, _volumeZ)));

        //vehicle.transfer(msg.value);
        (bool success, ) = vehicle.call.value(msg.value)("");
        require(success, "Transfer failed.");
    }

    function getRequests_1(uint _seq) public view returns(int[] memory _sourceX, int[] memory _sourceY,
                                    		            int[] memory _destinationX, int[] memory _destinationY) {

        uint _len = requests[_seq].length;
        _sourceX      = new  int[](_len);
        _sourceY      = new  int[](_len);
        _destinationX = new  int[](_len);
        _destinationY = new  int[](_len);

        for(uint i=0; i < _len; i++) {
            _sourceX[i]      = requests[_seq][i].source.x;
            _sourceY[i]      = requests[_seq][i].source.y;
            _destinationX[i] = requests[_seq][i].destination.x;
            _destinationY[i] = requests[_seq][i].destination.y;
        }
    }

    function getRequests_2(uint _seq) public view returns(uint[] memory _weight,
                                                          uint[] memory _volumeX,
                                                          uint[] memory _volumeY,
                                                          uint[] memory _volumeZ) {

        uint _len = requests[_seq].length;
        _weight       = new uint[](_len);
        _volumeX      = new uint[](_len);
        _volumeY      = new uint[](_len);
        _volumeZ      = new uint[](_len);
        for(uint i=0; i < _len; i++) {
            _weight[i]  = requests[_seq][i].weight;
            _volumeX[i] = requests[_seq][i].volume.len;
            _volumeY[i] = requests[_seq][i].volume.height;
            _volumeZ[i] = requests[_seq][i].volume.depth;
        }
    }

    function getNumberOfRequests(uint _seq) public view returns(uint) {
        return requests[_seq].length;
    }

    function getFeeDistanceRatio() public view returns(uint) {
        return feeDistanceRatio;
    }

}
