#!/usr/bin/env python3
"""Generated standalone test program 271; profile: instant."""
PROGRAM_ID = 271

def divide(left: str, right: str) -> float | None:
    try:
        return float(left) / float(right)
    except (ValueError, ZeroDivisionError):
        return None

def main() -> None:
    assert divide("12", "3") == 4 and divide("x", "0") is None
if __name__ == "__main__": main()

# Timing profile: normally well below one millisecond.
