#!/usr/bin/env python3
"""Generated standalone test program 040; profile: two_seconds."""
PROGRAM_ID = 40

from pathlib import Path
import tempfile

def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "dummy.txt"
        path.write_text("red\nblue\ngreen\n", encoding="utf-8")
        lengths = {line: len(line) for line in path.read_text().splitlines()}
        assert lengths["green"] == 5
if __name__ == "__main__": main()

# Timing profile: approximately two wall-clock seconds.
import time
_started = time.perf_counter()
while time.perf_counter() - _started < 2.0:
    pass
