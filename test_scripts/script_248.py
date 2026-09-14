#!/usr/bin/env python3
"""Generated standalone test program 248; profile: instant."""
PROGRAM_ID = 248

def cubes(limit: int):
    return (number ** 3 for number in range(limit) if number % 2)

def main() -> None:
    values = [value for value in cubes(8)]
    assert values == [1, 27, 125, 343]
if __name__ == "__main__": main()

# Timing profile: normally well below one millisecond.
