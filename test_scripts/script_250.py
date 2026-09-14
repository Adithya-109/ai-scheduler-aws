#!/usr/bin/env python3
"""Generated standalone test program 250; profile: ten_seconds."""
PROGRAM_ID = 250

def main() -> None:
    counter, collected = 0, []
    while counter < 12:
        if counter % 3 == 0: collected.append(counter * counter)
        counter += 1
    assert collected == [0, 9, 36, 81]
if __name__ == "__main__": main()

# Timing profile: at least ten seconds of CPU-intensive integer arithmetic.
import time
_started, _state = time.perf_counter(), 1
while time.perf_counter() - _started < 10.0:
    _state = ((_state * 1_103_515_245) + 12_345) & 0x7FFFFFFF
assert _state >= 0
