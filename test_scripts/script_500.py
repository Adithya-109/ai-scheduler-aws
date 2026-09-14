#!/usr/bin/env python3
"""Generated standalone test program 500; profile: ten_seconds."""
PROGRAM_ID = 500

def cubes(limit: int):
    return (number ** 3 for number in range(limit) if number % 2)

def main() -> None:
    values = [value for value in cubes(8)]
    assert values == [1, 27, 125, 343]
if __name__ == "__main__": main()

# Timing profile: at least ten seconds of CPU-intensive integer arithmetic.
import time
_started, _state = time.perf_counter(), 1
while time.perf_counter() - _started < 10.0:
    _state = ((_state * 1_103_515_245) + 12_345) & 0x7FFFFFFF
assert _state >= 0
