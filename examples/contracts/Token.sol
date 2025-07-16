pragma solidity ^0.8.0;

import "./MathLib.sol";

contract Token {
    using MathLib for uint;

    mapping(address => uint) public balances;

    function deposit() external payable {
        balances[msg.sender] = balances[msg.sender].increment(msg.value);
    }

    function withdraw(uint amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] = balances[msg.sender].decrement(amount);
        _transfer(msg.sender, amount);
    }

    function _transfer(address to, uint amount) internal {
        payable(to).transfer(amount);
    }
}
