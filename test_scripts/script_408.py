#!/usr/bin/env python3
"""Generated standalone test program 408; profile: instant."""
PROGRAM_ID = 408

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int
    def move(self, dx: int = 0, dy: int = 0) -> "Point": return Point(self.x + dx, self.y + dy)

def main() -> None:
    assert Point(2, 3).move(dx=-1, dy=4) == Point(1, 7)
if __name__ == "__main__": main()

# Timing profile: normally well below one millisecond.
