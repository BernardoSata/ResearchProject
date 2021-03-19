// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;

//import * as P from "./PlanningLib.sol";

contract VehicleInt {
    function returnFunds(uint _funds) public {}
    function getVehiclesNumber(uint _seq) public view returns(uint) {}
    function update() public {}
}

contract VotersOracle {

    uint256 public newly_opened_seq = 0;    
    uint256 public last_finalized_seq;

	address public owner = msg.sender;
    address payable public vehicle;
	
	address payable[] internal voters;						// Keeps track of voters

	uint256 public numOfTotalVoters = 0;
	uint256 public initial_Deposit = 10**18;                 // 1 Ether

	mapping (address => bool) public knownVoters;         	// Voter is known/or not
    mapping (address => bool) public allowedVoters;		  	// Voter has paid the entry fee
    mapping (address => uint32) public voterSeed;			// Seed to be used in the solution computation

    VehicleInt vehCon;

    event newVoterSeed(address voter, uint32 seed);

	modifier restricted() {
        require(msg.sender == owner,
        "This function is restricted to the contract's owner");
        _;
    }

	modifier onlyVoters() {
        require(allowedVoters[msg.sender],"This function is restricted to accredited voters");
        _;
    }

    function setNewOwner(address _newOwner) public restricted {
        owner = _newOwner;
    }
    
    function removeIndex(uint index) internal {
    	voters[index] = voters[voters.length-1];
  		delete voters[voters.length-1];
  		//voters.length--;
    }
    
    function removeAddress(address _add) internal {
    	for(uint i=0; i<voters.length; i++) {
    		if(voters[i] == _add) {
    			removeIndex(i);
    			return;
    		}
    	}
    }
        
    function setInitialDeposit(uint value) public restricted {
    	initial_Deposit = value;
    	return;
    }

    function setVehCon(address payable _vehAdd) public restricted {
        vehicle = _vehAdd;
        vehCon = VehicleInt(_vehAdd);
    }

    function addVoter(address _newVoter) public restricted {
    	knownVoters[_newVoter] = true;
    }
    
    function enableVoter() public payable {
    	require(allowedVoters[msg.sender] != true, "This voter is already enabled");
    	require(knownVoters[msg.sender],"This function is restricted to accredited voters");
    	require(msg.value >= initial_Deposit, "Not enough funds were sent to be accepted");
        allowedVoters[msg.sender] = true;
        numOfTotalVoters ++;
        voters.push(msg.sender);
        voterSeed[msg.sender] = uint32(uint(keccak256(abi.encode(msg.sender))));	// Pseudo-random seed generated for the new voter
        (bool success, ) = vehicle.call.value(msg.value)("");
        require(success, "Transfer failed.");
        emit newVoterSeed(msg.sender, voterSeed[msg.sender]);
    }
    
    function leaveVoters() public {
        if(allowedVoters[msg.sender] == true) {
            allowedVoters[msg.sender] = false;
            knownVoters[msg.sender] = false;
            vehCon.returnFunds(initial_Deposit);
            //msg.sender.transfer(initial_Deposit);
            (bool success, ) = msg.sender.call.value(initial_Deposit)("");
            require(success, "Transfer failed.");
            removeAddress(msg.sender);
            numOfTotalVoters --;
            return;
        }
        if(knownVoters[msg.sender] == true) {
            knownVoters[msg.sender] = false;
            return;
        }
    }

    function removeFrauder(address _fraudVoter) internal {
    	require(allowedVoters[_fraudVoter],"The fraudulent voter is not among the enabled ones");
    	allowedVoters[_fraudVoter] = false;
    	uint fee = initial_Deposit / (numOfTotalVoters - 1);
    	uint fraudIndex;
    	for(uint i=0; i<numOfTotalVoters; i++) {
    		if(voters[i] == _fraudVoter) {
                fraudIndex = i;
                continue;
            }
            //voters[i].transfer(fee);
            (bool success, ) = voters[i].call.value(fee)("");
            require(success, "Transfer failed.");
    	}
    	numOfTotalVoters --;
    	removeIndex(fraudIndex);
    }
    
    function punishFrauder(address _fraudVoter, address _disputer) internal {
    	require(allowedVoters[_fraudVoter],"The fraudulent voter is not among the enabled ones");
    	allowedVoters[_fraudVoter] = false;
    	uint fee = initial_Deposit / numOfTotalVoters;
    	uint fraudIndex;
    	for(uint i=0; i<numOfTotalVoters; i++) {
    		if(voters[i] == _fraudVoter) fraudIndex = i;
    		if(voters[i] == _disputer) {
    			//voters[i].transfer(fee * 2);
                (bool success, ) = voters[i].call.value(fee * 2)("");
                require(success, "Transfer failed.");
    		}
    		else {
                //voters[i].transfer(fee);
                (bool success, ) = voters[i].call.value(fee)("");
                require(success, "Transfer failed.");
            }
    	}
    	numOfTotalVoters --;
    	removeIndex(fraudIndex);
    }

    function getInitial_Deposit() public view returns(uint) {
        return initial_Deposit;
    }

    receive() external payable {}
    fallback() external payable {}
}
