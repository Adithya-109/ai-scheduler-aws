#!/usr/bin/env python3
"""Generated standalone test program 010; profile: two_seconds."""
PROGRAM_ID = 10

def main() -> None:
    counter, collected = 0, []
    while counter < 12:
        if counter % 3 == 0: collected.append(counter * counter)
        counter += 1
    assert collected == [0, 9, 36, 81]
if __name__ == "__main__": main()

# Timing profile: approximately two wall-clock seconds.
import time
_started = time.perf_counter()
while time.perf_counter() - _started < 2.0:
    pass
