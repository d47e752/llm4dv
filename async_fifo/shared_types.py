from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Stimulus:
    value: Optional[List]
    finish: bool

@dataclass
class DUTState:

    def state_vector(self):
        return []
    
class CoverageDatabase:
    misc_bins: dict[str, int]


"""
Operations:
-Read
-Write

BIN LIST:
-Full
-Empty
-Read pointer wrap (full-return to 0, gray-MSB toggles)
-Write pointer wrap (full-return to 0, gray-MSB toggles)
-Underflow
-Overflow
-Simultanious read and write (and vice versa)
"""