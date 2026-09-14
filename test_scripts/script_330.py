#!/usr/bin/env python3
"""Generated standalone test program 330; profile: two_seconds."""
PROGRAM_ID = 330

def classify(value: object) -> str:
    if isinstance(value, int):
        if value < 0: return "negative"
        if value == 0: return "zero"
        return "even-positive" if value % 2 == 0 else "odd-positive"
    if isinstance(value, str): return "short-text" if len(value) < 5 else "long-text"
    return "other"

def main() -> None:
    assert [classify(x) for x in (-2, 0, 7, "hello")] == ["negative", "zero", "odd-positive", "long-text"]
if __name__ == "__main__": main()

# Timing profile: approximately two wall-clock seconds.
import time
_started = time.perf_counter()
while time.perf_counter() - _started < 2.0:
    pass
