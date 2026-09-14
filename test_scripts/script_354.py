#!/usr/bin/env python3
"""Generated standalone test program 354; profile: instant."""
PROGRAM_ID = 354

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

# Timing profile: normally well below one millisecond.
