#!/usr/bin/env python3
"""Generated standalone test program 017; profile: instant."""
PROGRAM_ID = 17

def main() -> None:
    total = 0
    for a in range(3):
        for b in range(3):
            for c in range(2):
                for d in range(2):
                    for e in range(2):
                        total += (a + b + c + d + e) % 3
    assert total >= 0
if __name__ == "__main__": main()

# Timing profile: normally well below one millisecond.
