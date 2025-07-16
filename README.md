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
shows the source for each function that it encounters.
