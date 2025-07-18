pragma solidity ^0.8.0;

contract SinkTest {
    function trigger(address payable t) external payable {
        t.call("");
        t.delegatecall("");
        t.staticcall("");
        t.callcode("");
        t.transfer(1 ether);
        t.send(1 ether);
        t.call{value: 1 ether}("");
        selfdestruct(t);
    }
}
