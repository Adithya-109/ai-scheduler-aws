#!/usr/bin/env python3
"""Generated standalone test program 290; profile: two_seconds."""
PROGRAM_ID = 290

def fibonacci(number: int, cache: dict[int, int] | None = None) -> int:
    cache = {} if cache is None else cache
    if number < 2: return number
    if number not in cache:
        cache[number] = fibonacci(number - 1, cache) + fibonacci(number - 2, cache)
    return cache[number]

def main() -> None:
    assert fibonacci(18) == 2584
if __name__ == "__main__": main()

# Timing profile: approximately two wall-clock seconds.
import time
_started = time.perf_counter()
while time.perf_counter() - _started < 2.0:
    pass
