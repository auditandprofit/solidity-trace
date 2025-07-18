from tracer import (
    run, extract_contract_body, _slice_by_lines,
    extract_snippet, collect_sinks
)


def test_run_echo():
    assert run(['echo', 'hello']).strip() == 'hello'


def test_extract_contract_body():
    src = (
        'pragma solidity ^0.8.0;\n\n'
        'contract C {\n'
        '    uint x;\n'
        '    function foo() public {}\n'
        '}\n'
    )
    start = src.index('contract C')
    length = src[start:].rindex('}') + 1
    offsets = {'C::': (start, length)}
    body = extract_contract_body(src, 'C', offsets)
    assert body == '\n    uint x;\n    function foo() public {}\n'


def test_slice_by_lines():
    src = 'a\nline2\nline3\n'
    start = src.index('line2')
    snippet, line_no = _slice_by_lines(src, start, len('line2\n'))
    assert snippet == 'line2\n'
    assert line_no == 2


def test_extract_snippet():
    src = (
        'contract C {\n'
        '    function foo() public {\n'
        '        uint a = 1;\n'
        '    }\n'
        '}\n'
    )
    start = src.index('function foo')
    end = src.index('\n    }', start) + len('\n    }')
    offsets = {'C::foo': (start, end - start)}
    snippet, line_no = extract_snippet(src, 'C::foo', offsets)
    assert 'uint a = 1' in snippet
    assert line_no == 2


def test_collect_sinks():
    src = (
        'pragma solidity ^0.8.0;\n\n'
        'contract SinkTest {\n'
        '    function trigger(address payable t) external payable {\n'
        '        t.call(\"\");\n'
        '        t.delegatecall(\"\");\n'
        '        t.staticcall(\"\");\n'
        '        t.callcode(\"\");\n'
        '        t.transfer(1 ether);\n'
        '        t.send(1 ether);\n'
        '        t.call{value: 1 ether}(\"\");\n'
        '        selfdestruct(t);\n'
        '    }\n'
        '}\n'
    )
    start = src.index('function trigger')
    end = src.index('\n    }', start) + len('\n    }')
    offsets = {'SinkTest::trigger': (start, end - start)}
    index = collect_sinks(src, offsets)
    sinks = index['SinkTest::trigger']
    assert len(sinks) == 8
    assert all(s in offsets for s in sinks)
