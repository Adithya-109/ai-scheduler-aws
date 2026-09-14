#!/usr/bin/env python3
"""Generated standalone test program 386; profile: instant."""
PROGRAM_ID = 386

def fibonacci(number: int, cache: dict[int, int] | None = None) -> int:
    cache = {} if cache is None else cache
    if number < 2: return number
    if number not in cache:
        cache[number] = fibonacci(number - 1, cache) + fibonacci(number - 2, cache)
    return cache[number]

def main() -> None:
    assert fibonacci(18) == 2584
if __name__ == "__main__": main()

# Timing profile: normally well below one millisecond.
