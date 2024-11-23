from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Stimulus:
    value: Optional[List]
    finish: bool

@dataclass
class DUTState:
    allocated_nodeslot: int

    def state_vector(self):
        return []
    
class CoverageDatabase:
    misc_bins: dict[str, int]


"""
Operations:
-Request weights with different precision
-Request adjacency list
-Request messages
-Request scale factors

BIN LIST:
-Request weights from all weight banks
-Message fetch with non-partial/partial adj queue
-Message fetch non-partial/partial
-Scale fetch non-partial/partial
"""