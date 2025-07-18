import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tracer import build_reverse, rev_paths


def test_rev_paths_simple():
    edges = [('A', 'B'), ('B', 'C'), ('D', 'C')]
    rev = build_reverse(edges)
    def is_entry(n):
        return n in {'A', 'D'}
    paths = list(rev_paths('C', rev, is_entry))
    assert sorted(paths) == [['A', 'B', 'C'], ['D', 'C']]
