pragma solidity ^0.8.0;

import "./Token.sol";

contract Wallet {
    Token public token;

    constructor(Token _token) {
        token = _token;
    }

    function deposit() external payable {
        token.deposit{value: msg.value}();
    }

    function withdraw(uint amount) external {
        token.withdraw(amount);
    }
}
