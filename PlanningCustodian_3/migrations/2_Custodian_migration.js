const RequestOracle = artifacts.require("RequestOracle");
const VehicleOracle = artifacts.require("VehicleOracle");
const Custodian     = artifacts.require("Custodian");

let accounts = web3.eth.getAccounts();

module.exports = function (deployer) {
  deployer.deploy(Custodian).then(function() {
  	return deployer.deploy(RequestOracle, Custodian.address).then(function() {
  		return deployer.deploy(VehicleOracle, Custodian.address);
  		});
  	//Custodian.setReqCon(RequestOracle.address, {from: accounts[0]});
	  //let cust = await Custodian.deployed();
	  //cust.setReqCon(RequestOracle.address).send({from: accounts[0]});
  });
};


/*
deployer.deploy(A).then(function() {
  return deployer.deploy(B, A.address);
});


var a, b;
deployer.then(function() {
  // Create a new version of A
  return A.new();
}).then(function(instance) {
  a = instance;
  // Get the deployed instance of B
  return B.deployed();
}).then(function(instance) {
  b = instance;
  // Set the new instance of A's address on B via B's setA() function.
  return b.setA(a.address);
});
*/
