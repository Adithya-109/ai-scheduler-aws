#!/usr/bin/env python3
"""Generated standalone test program 076; profile: instant."""
PROGRAM_ID = 76

from pathlib import Path
import tempfile

def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "dummy.txt"
        path.write_text("red\nblue\ngreen\n", encoding="utf-8")
        lengths = {line: len(line) for line in path.read_text().splitlines()}
        assert lengths["green"] == 5
if __name__ == "__main__": main()

# Timing profile: normally well below one millisecond.
