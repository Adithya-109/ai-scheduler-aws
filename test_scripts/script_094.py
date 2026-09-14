#!/usr/bin/env python3
"""Generated standalone test program 094; profile: instant."""
PROGRAM_ID = 94

def main() -> None:
    counter, collected = 0, []
    while counter < 12:
        if counter % 3 == 0: collected.append(counter * counter)
        counter += 1
    assert collected == [0, 9, 36, 81]
if __name__ == "__main__": main()

# Timing profile: normally well below one millisecond.
