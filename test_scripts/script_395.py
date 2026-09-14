#!/usr/bin/env python3
"""Generated standalone test program 395; profile: instant."""
PROGRAM_ID = 395

from collections import Counter

def main() -> None:
    text = "Sphinx of black quartz, judge my vow!"
    normalized = "".join(character.lower() for character in text if character.isalpha())
    counts = Counter(normalized)
    assert counts["q"] == 1 and normalized.startswith("sphinx")
if __name__ == "__main__": main()

# Timing profile: normally well below one millisecond.
