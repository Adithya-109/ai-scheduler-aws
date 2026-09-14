#!/usr/bin/env python3
"""Generated standalone test program 207; profile: instant."""
PROGRAM_ID = 207

class Ledger:
    def __init__(self, owner: str, *entries: int) -> None:
        self.owner, self.entries = owner, list(entries)
    @property
    def balance(self) -> int: return sum(self.entries)
    def add(self, amount: int) -> "Ledger": self.entries.append(amount); return self

def main() -> None:
    ledger = Ledger("Ada", 3, -1).add(9)
    assert ledger.balance == 11 and ledger.owner == "Ada"
if __name__ == "__main__": main()

# Timing profile: normally well below one millisecond.
