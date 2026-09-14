#!/usr/bin/env python3
"""Generated standalone test program 100; profile: ten_seconds."""
PROGRAM_ID = 100

from pathlib import Path
import tempfile

def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "dummy.txt"
        path.write_text("red\nblue\ngreen\n", encoding="utf-8")
        lengths = {line: len(line) for line in path.read_text().splitlines()}
        assert lengths["green"] == 5
if __name__ == "__main__": main()

# Timing profile: at least ten seconds of CPU-intensive integer arithmetic.
import time
_started, _state = time.perf_counter(), 1
while time.perf_counter() - _started < 10.0:
    _state = ((_state * 1_103_515_245) + 12_345) & 0x7FFFFFFF
assert _state >= 0
