pragma solidity ^0.8.0;

library MathLib {
    function increment(uint self, uint amount) internal pure returns (uint) {
        return self + amount;
    }
    function decrement(uint self, uint amount) internal pure returns (uint) {
        return self - amount;
    }
}
