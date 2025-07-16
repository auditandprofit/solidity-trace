#!/usr/bin/env python3
"""
trace_with_src.py  <Contract::entryFunc>  <*.sol …>

Print every call-chain that Surya finds **plus** the Solidity source for
each node. Rough Python port of the earlier Bash snippet.

Requires:
    • surya  (npm install -g surya)
    • jq     (brew install jq)   ← only if you keep the shell fall-back
    • Python ≥3.8

Example
    python trace_with_src.py Token::withdraw contracts/*.sol
"""

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

def run(cmd: list[str], **kw) -> str:
    """Run a command and return stdout, or raise if non-zero."""
    res = subprocess.run(cmd, check=True, text=True, capture_output=True, **kw)
    return res.stdout

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entry", help="Entry point e.g. MyToken::withdraw")
    ap.add_argument("files", nargs="+", help="*.sol sources (glob them yourself)")
    args = ap.parse_args()

    # temp work dir
    with tempfile.TemporaryDirectory() as tmp:
        flat  = Path(tmp, "flat.sol")
        trace = Path(tmp, "trace.json")

        # 1) flattened source
        flat.write_text(run(["surya", "flatten", *args.files]))

        # 2) JSON call-graph
        trace.write_text(run(["surya", "ftrace", args.entry, "all",
                              *args.files, "-j"]))

        src_text = flat.read_text()
        data = json.loads(trace.read_text())
        nodes = {n["id"]: n for n in data["nodes"]}

        print(f"\n== Call-chains for {args.entry} ==\n")

        for edge in data["edges"]:
            node = nodes[edge["source"]]
            name, src = node["name"], node["src"]  # "start:length:fileIndex"
            start, length, *_ = map(int, src.split(":"))
            snippet = src_text[start:start + length]
            print(f"### {name}\n{snippet}\n")

if __name__ == "__main__":
    # Guard against missing binaries early
    for bin_ in ("surya",):
        if not shutil.which(bin_):
            raise SystemExit(f"{bin_} not found in PATH")
    main()

