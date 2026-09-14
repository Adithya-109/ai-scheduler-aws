#!/usr/bin/env python3
"""Generated standalone test program 050; profile: ten_seconds."""
PROGRAM_ID = 50

def fibonacci(number: int, cache: dict[int, int] | None = None) -> int:
    cache = {} if cache is None else cache
    if number < 2: return number
    if number not in cache:
        cache[number] = fibonacci(number - 1, cache) + fibonacci(number - 2, cache)
    return cache[number]

def main() -> None:
    assert fibonacci(18) == 2584
if __name__ == "__main__": main()

# Timing profile: at least ten seconds of CPU-intensive integer arithmetic.
import time
_started, _state = time.perf_counter(), 1
while time.perf_counter() - _started < 10.0:
    _state = ((_state * 1_103_515_245) + 12_345) & 0x7FFFFFFF
assert _state >= 0
