#!/usr/bin/env python3
"""Trace Solidity call chains with source snippets.

Usage:
    python tracer.py <Contract::func> <files...>

Requires `surya` to be installed and available in PATH.
"""
import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(cmd):
    res = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return res.stdout


def parse_ftrace(text):
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    functions = []
    for line in text.splitlines():
        line = ansi.sub('', line)
        line = line.lstrip('│ ').lstrip('└─').strip()
        if not line:
            continue
        if '::' not in line:
            continue
        func = line.split()[0]
        functions.append(func)
    return functions


def extract_snippet(src: str, func: str) -> str | None:
    """Return the Solidity code for `func` from `src`.

    This performs a very small amount of parsing by locating the contract
    definition first and then searching for the function inside that block.
    """
    contract, name = func.split("::", 1)

    # Find contract or library body
    c_pat = re.compile(r"(contract|library)\s+" + re.escape(contract) + r"\b[^\{]*\{",
                       re.MULTILINE)
    m_contract = c_pat.search(src)
    if not m_contract:
        return None
    c_start = m_contract.end()
    idx = c_start
    depth = 1
    while idx < len(src) and depth > 0:
        if src[idx] == '{':
            depth += 1
        elif src[idx] == '}':
            depth -= 1
        idx += 1
    contract_body = src[c_start:idx-1]

    # Now search for the function within the contract body
    f_pat = re.compile(r"function\s+" + re.escape(name) + r"\b[^\{]*\{",
                       re.MULTILINE)
    m_func = f_pat.search(contract_body)
    if not m_func:
        return None
    f_start = m_func.start()
    idx2 = m_func.end()
    depth = 1
    while idx2 < len(contract_body) and depth > 0:
        if contract_body[idx2] == '{':
            depth += 1
        elif contract_body[idx2] == '}':
            depth -= 1
        idx2 += 1
    return contract_body[f_start:idx2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('entry', help='Entry point CONTRACT::FUNCTION')
    ap.add_argument('files', nargs='+', help='Solidity sources')
    args = ap.parse_args()

    for bin_ in ('surya',):
        if not shutil.which(bin_):
            raise SystemExit(f'{bin_} not found in PATH')

    with tempfile.TemporaryDirectory() as tmp:
        flat = Path(tmp, 'flat.sol')
        flat.write_text(run(['surya', 'flatten', *args.files]))
        trace = run(['surya', 'ftrace', args.entry, 'all', *args.files])

        src_text = flat.read_text()
        funcs = parse_ftrace(trace)

        print(f"\n== Call Trace for {args.entry} ==\n")
        for f in funcs:
            snippet = extract_snippet(src_text, f)
            print(f'### {f}')
            if snippet:
                print(snippet)
            else:
                print('[source not found]')
            print()

if __name__ == '__main__':
    main()
