# Solidity Trace

This repository contains a small Python script to inspect Solidity call traces
along with the source code for each function in the chain. It relies on
[Surya](https://github.com/ConsenSys/surya) to generate a call graph which is
then parsed to show the relevant Solidity snippets.

## Requirements

- Python 3.8 or newer
- `surya` available in your `PATH`

Install Surya with npm:

```bash
npm install -g surya
```

## Usage

```bash
python tracer.py <CONTRACT::FUNCTION> <files...>
```

For example, using the contracts in `examples/`:

```bash
python tracer.py Token::withdraw examples/contracts/*.sol
```

The script prints the chain of calls starting from the given entry point and
shows the source for each function that it encounters. Calls added through
`using` library directives are also followed, so library functions invoked as
extensions of built-in types will appear in the trace.

To inspect the callers leading to a particular value transfer sink instead,
use the `--from-sink` flag with the sink identifier printed by a regular run:

```bash
python tracer.py --from-sink Token::_transfer::SINK::transfer::0 examples/contracts/*.sol
```

Each reverse trace prints all possible entry points that can reach the sink.

By default the trace also highlights low level calls and value transfer
sinks (e.g. `transfer`, `selfdestruct`, `call{value: ...}`). Use the
`--no-sinks` flag to suppress this extra information if a compact output
is desired.
