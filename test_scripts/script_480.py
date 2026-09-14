#!/usr/bin/env python3
"""Generated standalone test program 480; profile: two_seconds."""
PROGRAM_ID = 480

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int
    def move(self, dx: int = 0, dy: int = 0) -> "Point": return Point(self.x + dx, self.y + dy)

def main() -> None:
    assert Point(2, 3).move(dx=-1, dy=4) == Point(1, 7)
if __name__ == "__main__": main()

# Timing profile: approximately two wall-clock seconds.
import time
_started = time.perf_counter()
while time.perf_counter() - _started < 2.0:
    pass
