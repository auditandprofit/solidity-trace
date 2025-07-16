#!/usr/bin/env python3
"""Trace Solidity call chains with source snippets.

This script calls Surya to obtain a call graph starting from a given
`CONTRACT::FUNCTION` and prints each function in the chain together with the
Solidity source code.

Example:
    python tracer.py Token::withdraw examples/contracts/*.sol

Surya must be installed and available in ``PATH``.
"""
import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def run(cmd):
    res = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return res.stdout


def parse_ftrace(text):
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    functions = []
    tree_prefix = re.compile(r'^[\s│├└─]+')
    for line in text.splitlines():
        line = ansi.sub('', line)
        line = tree_prefix.sub('', line)
        if not line:
            continue
        if '::' not in line:
            continue
        func = line.split()[0]
        functions.append(func)
    return functions


def extract_contract_body(src: str, contract: str) -> Optional[str]:
    """Return the full body of a contract or library."""
    c_pat = re.compile(
        r"(contract|library)\s+" + re.escape(contract) + r"\b[^\{]*\{",
        re.MULTILINE,
    )
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
    return src[c_start : idx - 1]


def parse_contract_vars(body: str, contract_names) -> dict:
    """Find state variables that reference known contracts."""
    if not contract_names:
        return {}
    pat = re.compile(
        r"\b(" + "|".join(map(re.escape, contract_names)) + r")\s+(?:[\w\s]+?\s)?(\w+)\s*(?:;|=)",
    )
    vars_ = {}
    for m in pat.finditer(body):
        ctype, name = m.groups()
        vars_[name] = ctype
    return vars_


def find_cross_calls(snippet: str, var_map: dict) -> list[str]:
    """Find calls made through contract variables."""
    if not var_map:
        return []
    names = "|".join(map(re.escape, var_map.keys()))
    call_pat = re.compile(r"\b(" + names + r")\.(\w+)\s*(?:\{|\()")
    calls = []
    for m in call_pat.finditer(snippet):
        var, func = m.groups()
        calls.append(f"{var_map[var]}::{func}")
    return calls


def extract_snippet(src: str, func: str) -> Optional[str]:
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
    description = (
        "Print the call chain for a Solidity function and show the source "
        "snippet for each function in that chain. Surya is used to "
        "generate the call graph."
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

        # gather contract names
        contract_names = re.findall(r"(?:contract|library)\s+(\w+)", src_text)

        # map of contract to variable->type
        contract_vars = {}
        for cname in contract_names:
            body = extract_contract_body(src_text, cname)
            if body is None:
                continue
            contract_vars[cname] = parse_contract_vars(body, contract_names)

        visited = set()
        stack = [args.entry]
        funcs = []

        while stack:
            func = stack.pop()
            if func in visited:
                continue
            visited.add(func)
            funcs.append(func)

            try:
                trace = run(['surya', 'ftrace', func, 'all', *args.files])
            except subprocess.CalledProcessError:
                trace = ''
            for f in parse_ftrace(trace):
                if f not in visited:
                    stack.append(f)

            snippet = extract_snippet(src_text, func)
            if not snippet:
                continue
            contract, _ = func.split('::', 1)
            vars_map = contract_vars.get(contract, {})
            for call in find_cross_calls(snippet, vars_map):
                if call not in visited:
                    stack.append(call)

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
