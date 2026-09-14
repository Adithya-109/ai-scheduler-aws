#!/usr/bin/env python3
"""Generated standalone test program 440; profile: two_seconds."""
PROGRAM_ID = 440

def cubes(limit: int):
    return (number ** 3 for number in range(limit) if number % 2)

def main() -> None:
    values = [value for value in cubes(8)]
    assert values == [1, 27, 125, 343]
if __name__ == "__main__": main()

# Timing profile: approximately two wall-clock seconds.
import time
_started = time.perf_counter()
while time.perf_counter() - _started < 2.0:
    pass
