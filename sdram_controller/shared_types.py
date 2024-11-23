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
BIN LIST:
Commands the controller can issue:
-Precharge current row
-Auto refresh
-Command inhibit
-Load mode register
-Activate
-Read
-Write
"""