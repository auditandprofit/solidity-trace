#!/usr/bin/env python3
"""Trace Solidity call chains with source snippets.

This script uses Surya's `ftrace` command with `--json` to obtain a call trace
starting from a given `CONTRACT::FUNCTION` and prints each function in the
chain together with the Solidity source code.

Example:
    python tracer.py Token::withdraw examples/contracts/*.sol

Surya must be installed and available in ``PATH``.
"""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Tuple


def run(cmd):
    res = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return res.stdout




def extract_contract_body(src: str, contract: str, offsets: dict) -> Optional[str]:
    """Return the full body of a contract or library using byte offsets."""
    off = offsets.get(contract + "::")
    if not off:
        return None
    start, length = map(int, off)
    snippet = src[start:start + length]
    first = snippet.find("{")
    last = snippet.rfind("}")
    if first == -1 or last == -1:
        return None
    return snippet[first + 1:last]












def _slice_by_lines(src: str, start: int, length: int) -> Tuple[str, int]:
    """Return the snippet and its first line number (1-based)."""
    first_line = src[:start].count("\n") + 1
    snippet = src[start : start + length]
    return snippet, first_line


def extract_snippet(
    src: str, func: str, offsets: dict
) -> Optional[Tuple[str, int]]:
    """Return (snippet, first_line) for `func`, or None if unavailable."""
    off = offsets.get(func)
    if not off:
        return None
    start, length = map(int, off)
    return _slice_by_lines(src, start, length)


def main():
    description = (
        "Print the call chain for a Solidity function and show the source "
        "snippet for each function in that chain. Surya's `ftrace` "
        "command is used to generate the trace."
    )
    epilog = (
        "Example:\n"
        "  python tracer.py Token::withdraw examples/contracts/*.sol"
    )
    ap = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        'entry',
        metavar='CONTRACT::FUNCTION',
        help='Entry point to start tracing',
    )
    ap.add_argument(
        'files',
        nargs='+',
        metavar='files',
        help='Solidity source files',
    )
    args = ap.parse_args()

    for bin_ in ('surya',):
        if not shutil.which(bin_):
            raise SystemExit(f'{bin_} not found in PATH')

    with tempfile.TemporaryDirectory() as tmp:
        flat = Path(tmp, 'flat.sol')
        flat.write_text(run(['surya', 'flatten', *args.files]))
        src_text = flat.read_text()

        describe = json.loads(run(['surya', 'describe', '--json', str(flat)]))
        offsets: Dict[str, tuple] = {}
        for c in describe.get('contracts', []):
            if 'src' in c:
                start, length, _ = c['src'].split(':')
                offsets[c['name'] + '::'] = (start, length)
            for f in c.get('functions', []):
                if 'src' not in f:
                    continue
                fs, fl, _ = f['src'].split(':')
                offsets[f"{c['name']}::{f['name']}"] = (fs, fl)

        trace = json.loads(
            run(['surya', 'ftrace', '--json', args.entry, 'all', str(flat)])
        )
        funcs = trace['trace']

        print(f"\n== Call Trace for {args.entry} ==\n")
        for f in funcs:
            res = extract_snippet(src_text, f, offsets)
            print(f'### {f}')
            if res:
                snippet, line_no = res
                print(f'// L{line_no}\n{snippet}')
            else:
                print('[source not found]')
            print()

if __name__ == '__main__':
    main()
