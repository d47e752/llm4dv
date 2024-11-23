from dataclasses import dataclass
from typing import Optional, List, Tuple
from pprint import pprint

@dataclass
class Stimulus:
    value: Optional[List]
    finish: bool

@dataclass
class DUTState:
    allocated_nodeslot: int

    def state_vector(self):
        return [
            self.allocated_nodeslot
        ]
    
class CoverageDatabase:

    misc_bins: dict[str, int]


"""
Operations:
-Allocate/deallocate tag
-Fetch adjacency list
-Fetch messages
-Fetch scale factors

BIN LIST:
-Operations when tag is deallocated
-Operations when nodeslots do not match
-Message fetch with non-partial/partial adj queue
-Message fetch performed
-Scale fetch performed
"""