from dataclasses import dataclass
from typing import Optional, List, Tuple
from pprint import pprint

BOUND = 64

@dataclass
class Stimulus:
    value: Optional[List[Tuple[int, int]]]
    finish: bool

@dataclass
class DUTState:
    reset_weights: int

    def state_vector(self):
        return [
            self.reset_weights
        ]
    
class CoverageDatabase:
    out_features: List[int]
    in_features: List[int]
    combined_features: List[List[int]]

    def output_coverage(self):
        print("****************** Out features *************")
        for i in range (1, BOUND+1):
            print(i, self.out_features[i])
        print("****************** In features *************")
        for i in range (1, BOUND/16+1):
            print(i, self.in_features[i])
        # TODO: print combined features
        
    # Flatten all coverage bins into a single vector (python list of integers)
    def get_coverage_vector(self):
        return (self.in_features + self.out_features)