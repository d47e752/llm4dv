# Copyright ***
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

from typing import List, Tuple, Any
from ibex_cpu.instructions import Encoding


class BaseFilter:
    def __call__(self, stimuli: List[int]) -> List[Any]:
        raise NotImplementedError


class Filter(BaseFilter):
    def __init__(self, lower_bound: int, upper_bound: int):
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    def __call__(self, stimuli: List[int]) -> List[int]:
        return list(
            filter(lambda x: self.lower_bound <= x <= self.upper_bound, stimuli)
        )
    
class AG_TFFilter(BaseFilter):
    def __init__(self, lower_bound: int, upper_bound: int):
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    def __call__(self, stimuli):
        filtered_stimuli = []
        # for i in stimuli:
        #     if(self.lower_bound <= i[0] <= self.upper_bound and self.lower_bound <= i[1] <= self.upper_bound):
        #         filtered_stimuli.append(i)
        filtered_stimuli = stimuli
        return filtered_stimuli
    
class AG_WBFilter(BaseFilter):
    def __init__(self, lower_bound: int, upper_bound: int):
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    def __call__(self, stimuli: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        filtered_stimuli = []
        # for i in stimuli:
        #     if(self.lower_bound <= i[0] <= self.upper_bound and self.lower_bound <= i[1] <= self.upper_bound):
        #         filtered_stimuli.append(i)
        filtered_stimuli = stimuli
        return filtered_stimuli


class ICFilter(BaseFilter):
    def __init__(self, lower_bound: int, upper_bound: int):
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    def __call__(self, updates: List[Tuple[int, int]]) -> List[List[Tuple[int, int]]]:
        return [list(
            filter(
                lambda p: self.lower_bound <= p[0] <= self.upper_bound
                and self.lower_bound <= p[1] <= self.upper_bound
                and Encoding(p[1]).typed() is not None,
                updates,
            )
        )]

class UniversalFilter(BaseFilter):
    def __init__(self, bound_list, hex_format = False):
        self.filter_list = bound_list
        self.hex_format = hex_format

    def __call__(self, stimuli):
        filtered_stimuli = [[0] * len(stimuli[0]) for _ in range(len(stimuli))]
        for i in range(len(stimuli)):
            for j in range(len(stimuli[i])):
                try:
                    if(self.filter_list[j] != None):
                        if(self.hex_format):
                            stimuli[i][j] = int(stimuli[i][j], 16)
                        else:
                            stimuli[i][j] = int(stimuli[i][j])
                        if(stimuli[i][j] < self.filter_list[j][0]): # check lower bound
                            stimuli[i][j] = self.filter_list[j][0]
                        if(stimuli[i][j] > self.filter_list[j][1]): # check upper bound
                            stimuli[i][j] = self.filter_list[j][1]
                    filtered_stimuli[i][j] = stimuli[i][j]
                except:
                        filtered_stimuli[i][j] = 0
        if(self.hex_format):
            for i in range(len(filtered_stimuli)):
                filtered_stimuli[i] = tuple(filtered_stimuli[i])
        return filtered_stimuli