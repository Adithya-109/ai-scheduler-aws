#!/usr/bin/env python3
"""Generated standalone test program 150; profile: ten_seconds."""
PROGRAM_ID = 150

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

# Timing profile: at least ten seconds of CPU-intensive integer arithmetic.
import time
_started, _state = time.perf_counter(), 1
while time.perf_counter() - _started < 10.0:
    _state = ((_state * 1_103_515_245) + 12_345) & 0x7FFFFFFF
assert _state >= 0
