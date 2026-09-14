#!/usr/bin/env python3
"""Generated standalone test program 385; profile: instant."""
PROGRAM_ID = 385

def transform(words: list[str], separator: str = "|") -> str:
    pieces = [word.strip().upper()[::-1] for word in words if word.strip()]
    return separator.join(f"{i:02d}:{piece}" for i, piece in enumerate(pieces))

def main() -> None:
    value = transform([" alpha ", "beta", "", "gamma"], separator=" ~ ")
    assert "AHPLA" in value
if __name__ == "__main__": main()

# Timing profile: normally well below one millisecond.
