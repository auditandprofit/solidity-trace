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
from collections import defaultdict
from typing import Optional, Dict, Tuple, List
import re


def run(cmd):
    res = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return res.stdout




def extract_contract_body(src: str, contract: str, offsets: dict) -> Optional[str]:
    """Return the full body of a contract or library using byte offsets."""
    off = offsets.get(contract + "::")
    if not off:
        return None
    start, length = off
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
    start, length = off
    return _slice_by_lines(src, start, length)


def collect_sinks(src: str, offsets: Dict[str, Tuple[int, int]]) -> Dict[str, List[str]]:
    """Detect low level calls and value sinks using regex heuristics."""
    patterns = {
        'call': re.compile(r'\.call\s*\('),
        'delegatecall': re.compile(r'\.delegatecall\s*\('),
        'staticcall': re.compile(r'\.staticcall\s*\('),
        'callcode': re.compile(r'\.callcode\s*\('),
        'transfer': re.compile(r'\.transfer\s*\('),
        'send': re.compile(r'\.send\s*\('),
        'selfdestruct': re.compile(r'\bselfdestruct\s*\('),
        'callvalue': re.compile(r'\.call\s*\{[^}]*value\s*:'),
    }

    func_index: Dict[str, List[str]] = defaultdict(list)

    for typ, regex in patterns.items():
        for m in regex.finditer(src):
            start = m.start()
            end = src.find(';', start)
            if end == -1:
                end = start + len(m.group(0))
            else:
                end += 1
            for fn, (fs, fl) in offsets.items():
                if fn.endswith('::'):
                    continue
                if fs <= start < fs + fl:
                    key = f"{fn}::SINK::{typ}::{len(func_index[fn])}"
                    offsets[key] = (start, end - start)
                    func_index[fn].append(key)
                    break

    return func_index


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
    ap.add_argument(
        '--no-sinks',
        action='store_true',
        help='Do not detect or print value transfer sinks',
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
        offsets: Dict[str, Tuple[int, int]] = {}
        for c in describe.get('contracts', []):
            if 'src' in c:
                start, length, _ = map(int, c['src'].split(':'))
                offsets[c['name'] + '::'] = (start, length)
            for f in c.get('functions', []):
                if 'src' not in f:
                    continue
                fs, fl, _ = map(int, f['src'].split(':'))
                offsets[f"{c['name']}::{f['name']}"] = (fs, fl)

        sink_index: Dict[str, List[str]] = {}
        if not args.no_sinks:
            sink_index = collect_sinks(src_text, offsets)

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

            if not args.no_sinks:
                for skey in sink_index.get(f, []):
                    sres = extract_snippet(src_text, skey, offsets)
                    if sres:
                        ssnip, sline = sres
                        print("### \ud83d\udd3b ValueTx sink in " + f)
                        print(f"// L{sline}\n{ssnip}")
            print()

if __name__ == '__main__':
    main()
