#!/usr/bin/env python3
"""Generated standalone test program 405; profile: instant."""
PROGRAM_ID = 405

def main() -> None:
    try:
        import numpy as np  # Optional: generated program remains dependency-free.
    except ImportError:
        matrix = [[1, 2], [3, 4]]
        trace = sum(matrix[i][i] for i in range(2))
    else:
        trace = int(np.trace(np.array([[1, 2], [3, 4]])))
    assert trace == 5
if __name__ == "__main__": main()

# Timing profile: normally well below one millisecond.
