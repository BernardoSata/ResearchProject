// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;

import "./VotersOracle.sol";

contract RequestInt {
    function getNumberOfRequests(uint _seq) public view returns(uint) {}
}

contract Custodian is VotersOracle {

    uint8 public THRESHOLD_OF_PARTICIPANTS = 100;

    // Nominal voting variables
    mapping(uint => mapping(address => uint)) public values;
    mapping(uint => mapping(address => uint[])) public genes;
    
    mapping (uint256 => uint256) public votesCountOnCamp;           // Total number of votes
    mapping (uint256 => address) public winner;                     // Final winner address
    mapping (uint256 => uint) public winnerValue;                   // Final declared values
    mapping (uint256 => uint[]) public winnerGene;                  // Final gene selected
    mapping (address => mapping (uint256 => bool)) clientHasVotedOnSeq;
    mapping (uint256 => bool) public campHasFinished;

    // Dispute voting variables
    uint disputeFunds = 10^6;                                       // weis for each voter

    mapping(uint256 => mapping(address => bool)) public dispVote;   // true: fraud, false: ok

    mapping (uint256 => uint256) public votesCountOnDisp;           // Total number of votes for dispute             
    mapping (address => mapping (uint256 => bool)) clientHasVotedOnDisp;
    mapping (uint256 => bool) public dispIsOpen;
    mapping (uint256 => bool) public disputeWon;
    mapping (uint256 => address) public disputeRaiser;

    RequestInt reqCon;

    // --------------------------------------------------------------
    event VoteCampFinished(uint256 seq, address winner, uint value, uint[] gene);
    event DisputeRaised(uint256 seq, address disputer, uint seed);
    event DisputeEnded(uint seq, bool won);

    // Warning: This function is only for experiments
    function unsafeSetVoterBase(uint256 _val) public { numOfTotalVoters = _val; }

    // Warning: This function is only for experiments
    function unsafeTerminateCurrentOpenedSeq() public {
        uint _seq = newly_opened_seq;
        //finalResultOnCamp[_seq] = [0];

        campHasFinished[_seq] = true;
        last_finalized_seq = _seq;
        newly_opened_seq = _seq + 1;
    }

    // Warning: This function is only for experiments
    function unsafeSetThreshold(uint8 _thresh) public { THRESHOLD_OF_PARTICIPANTS = _thresh; }

    // Warning: This function is only for experiments
    function unsafeFirstCycle() public restricted {
        last_finalized_seq = newly_opened_seq;
        newly_opened_seq = newly_opened_seq + 1;
    }

    function setReqCon(address _reqAdd) public restricted {
        reqCon = RequestInt(_reqAdd);
    }
    
    // ------------------------ VOTING MANAGEMENT --------------------

    function acceptVote(uint _value, uint[] memory _gene) public onlyVoters {
        
        address client = msg.sender;
                
        // Each client has single vote on a Seq
        if (clientHasVotedOnSeq[client][newly_opened_seq]) revert("Each client can only vote once");
        clientHasVotedOnSeq[client][newly_opened_seq] = true;
        
        // update total counts
        votesCountOnCamp[newly_opened_seq] = votesCountOnCamp[newly_opened_seq] + 1;
        
        // update vote
        values[newly_opened_seq][client] = _value;
        genes[newly_opened_seq][client] = _gene;
        
        // check finalization
        if ((votesCountOnCamp[newly_opened_seq] >= (THRESHOLD_OF_PARTICIPANTS * numOfTotalVoters / 100))) {
            // Compute the final result
            address _winner = computeWinner();
            winner[newly_opened_seq] = _winner;
            winnerValue[newly_opened_seq] = values[newly_opened_seq][_winner];
            winnerGene[newly_opened_seq] = genes[newly_opened_seq][_winner];

            campHasFinished[newly_opened_seq] = true;
            last_finalized_seq = newly_opened_seq;
            newly_opened_seq = newly_opened_seq + 1;

            vehCon.update();
            
            emit VoteCampFinished(last_finalized_seq, winner[last_finalized_seq], winnerValue[last_finalized_seq], winnerGene[last_finalized_seq]);
        } 
    }

    function computeWinner() private returns(address) {
        uint index = 0;
        while(clientHasVotedOnSeq[voters[index]][newly_opened_seq] != true) index ++; // Find the first client who voted
        
        uint minCost = values[newly_opened_seq][voters[index]];
        address argMinCost = voters[index];
        for(uint i=index+1; i < voters.length; i++) {
            for(uint j=index+1; j < voters.length; j++) {
            	if(clientHasVotedOnSeq[voters[j]][newly_opened_seq] != true) continue;
                if(values[newly_opened_seq][voters[j]] < minCost) {
                    minCost = values[newly_opened_seq][voters[j]];
                    argMinCost = voters[j];
                }
            }
            if(allRequestsUsed(argMinCost)) {
                return argMinCost;
            }
            values[newly_opened_seq][argMinCost] = 1e50;  // It will not be considered in the next computation
        }
        revert("No solution was found to be correct");
    }

    function allRequestsUsed(address _voter) private returns(bool) {
        bool found;
        uint req_len = reqCon.getNumberOfRequests(newly_opened_seq);
        uint veh_len = vehCon.getVehiclesNumber(newly_opened_seq);

        if (genes[newly_opened_seq][_voter].length != req_len*veh_len) {
            removeFrauder(_voter);
            //revert("1"); // Debug purpose
            return false;            // Wrong format
        }
        for(uint i=1; i<=req_len; i++) {
            found = false;
            for(uint j=0; j<genes[newly_opened_seq][_voter].length; j++) {
                if(genes[newly_opened_seq][_voter][j] == i) {
                    if(found == true) {
                        removeFrauder(_voter);
                        //revert("2"); // Debug purpose
                        return false;     // Same request assigned two times
                    }
                    found = true;
                }
            }
            if(found == false) {
                removeFrauder(_voter);
                //revert("3"); // Debug purpose
                return false;            // Request never assigned
            }
        }
        return true;
    }

    function getLastVoting() public view returns(address, uint, uint[] memory) {
        return (winner[last_finalized_seq], winnerValue[last_finalized_seq], winnerGene[last_finalized_seq]);
    }

    function getVotingBySeq(uint256 _seq) public view returns(address, uint, uint[] memory) {
        return (winner[_seq], winnerValue[_seq], winnerGene[_seq]);
    }

    function OpenedSeq() public view returns (uint256) {
        return newly_opened_seq;
    }

    // ------------------------ DISPUTE MANAGEMENT ----------------------
    function raiseDispute(uint _seq) public payable onlyVoters {
        require(msg.value >= voters.length * disputeFunds, "Not enough funds were sent to raise a dispute");
        require(campHasFinished[_seq], "The selected campaing has not ended yet");
        dispIsOpen[_seq] = true;
        disputeRaiser[_seq] = msg.sender;
        emit DisputeRaised(_seq, msg.sender, voterSeed[winner[_seq]]);
    }

    function acceptDisputeVote(uint _seq, bool vote) public onlyVoters { // Might need to send a hash instead of a bool + transfer only voting in accordance with the decision
        
        if (dispIsOpen[_seq] != true) revert("This dispute is closed");

        address payable client = msg.sender;
        
        // Winner and Disputer are not allowed to vote
        if (client == disputeRaiser[_seq] || client == winner[_seq]) revert("Winner and Disputer are not allowed to vote");

        // Each client has single vote on a Seq
        if (clientHasVotedOnDisp[client][_seq]) revert("Each client can only vote once");
        clientHasVotedOnDisp[client][_seq] = true;
        //client.transfer(disputeFunds);
        (bool success, ) = client.call.value(disputeFunds)("");
        require(success, "Transfer failed.");
        
        // update total counts
        votesCountOnDisp[_seq] = votesCountOnDisp[_seq] + 1;
        
        // update vote
        dispVote[_seq][client] = vote;

        // check finalization
        if ((votesCountOnDisp[_seq] >= (THRESHOLD_OF_PARTICIPANTS * (numOfTotalVoters - 2) / 100))) {
            // Compute the final result
            disputeWon[_seq] = dispWasWon(_seq);
            dispIsOpen[_seq] = false;
            
            if (disputeWon[_seq]) {
                punishFrauder(winner[_seq], disputeRaiser[_seq]);
            }
            emit DisputeEnded(_seq, disputeWon[_seq]);
        } 
    }

    function dispWasWon(uint _seq) private view returns(bool) {
        uint8 trues = 0;

        for(uint i=0; i < voters.length; i++) {
            if (clientHasVotedOnDisp[voters[i]][_seq] != true) continue;
            if (dispVote[_seq][voters[i]]) trues++;
            else trues--;
        }

        if (trues > 0) return true;     // true: fraud, 51% of voters to invalidate
        else return false;              // false: ok
    }
}
