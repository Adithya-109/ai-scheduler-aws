#!/usr/bin/env python3
"""Generated standalone test program 300; profile: ten_seconds."""
PROGRAM_ID = 300

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int
    def move(self, dx: int = 0, dy: int = 0) -> "Point": return Point(self.x + dx, self.y + dy)

def main() -> None:
    assert Point(2, 3).move(dx=-1, dy=4) == Point(1, 7)
if __name__ == "__main__": main()

# Timing profile: at least ten seconds of CPU-intensive integer arithmetic.
import time
_started, _state = time.perf_counter(), 1
while time.perf_counter() - _started < 10.0:
    _state = ((_state * 1_103_515_245) + 12_345) & 0x7FFFFFFF
assert _state >= 0
