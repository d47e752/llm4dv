# Copyright ***
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

import re
from abc import abstractmethod
from typing import List, Tuple, Optional


class BaseExtractor:
    @abstractmethod
    def __call__(self, text: str):
        raise NotImplementedError

    @abstractmethod
    def reset(self):
        raise NotImplementedError


class DumbExtractor(BaseExtractor):
    def __init__(self):
        super().__init__()

    def __call__(self, text: str) -> List[int]:
        literals = list(
            re.findall(r"(?:0x[\da-fA-F]+)|(?:-?\d+(?!\d)(?!\.)(?!:))", text, re.I)
        )
        numbers = list(
            map(lambda x: (int(x, 16) if x[:2] == "0x" else int(x)), literals)
        )
        return numbers

    def reset(self):
        pass

class AG_FTExtractor(BaseExtractor):
    def __init__(self):
        super().__init__()
    def __call__(self, text: str) -> List[Tuple[int, int]]:
        print(text)
        stimuli = []
        stim_str = text.replace("(", "").replace(")", "").replace('"', "").replace("'", "").replace("[", "").replace(" ", "").replace("]", "").replace("\n", "").split(",")
        i = 0
        while (i+3 < len(stim_str)-1):
            stimuli.append([str(stim_str[i]), int(stim_str[i+1]), int(stim_str[i+2]), int(stim_str[i+3])])
            i += 4
        return stimuli
    
    def reset(self):
        pass

class AG_WBExtractor(BaseExtractor):
    def __init__(self):
        super().__init__()
    # (a,b),(c,d),(e,f)
    def __call__(self, text: str) -> List[Tuple[int, int]]:
        stimuli = []
        stim_str = text.replace("(", "").replace(")", "").replace("[", "").replace("]", "").split(",")
        i = 0
        while (i < len(stim_str)-1):
            stimuli.append([int(stim_str[i]), int(stim_str[i+1])])
            i += 2
        return stimuli
    
    def reset(self):
        pass

class ICExtractor(BaseExtractor):
    def __init__(self):
        super().__init__()

    def __call__(self, text: str) -> List[Tuple[int, int]]:
        print(text)
        if(text[-1] != "]"):
            text = "),".join(text.split("),")[:-1]) + ")]"
        pairs: List[str] = list(
            re.findall(r"\(\"?'?0x[\da-fA-F]+'?\"?, ?\"?'?0x[\da-fA-F]+'?\"?\)", text, re.I)
        )
        updates = list(
            map(
                lambda t: tuple(map(
                    lambda x: int(x, 16), t[1:-1].replace("'", "").replace('"', '').split(",")
                ))[:2],
                pairs,
            )
        )
        return updates

    def reset(self):
        pass

class UniversalExtractor(BaseExtractor):
    def __init__(self, stim_seq_length):
        super().__init__()
        self.stim_seq_length = stim_seq_length

    def __call__(self, text):
        print("===============================")
        print(text)
        stimuli = []
        if("[" in text):
            text = "[".join(text.split("[")[1:])
        stim_str = text.replace("*", "").replace("(", "").replace(")", "").replace('"', "").replace("'", "").replace("[", "").replace(" ", "").replace("]", "").replace("\n", "").split(",")
        i = 0
        while ((i + self.stim_seq_length - 1) <= len(stim_str)-1):
            current_stimulus = []
            for j  in range(self.stim_seq_length):
                current_stimulus.append(stim_str[i+j])
            stimuli.append(current_stimulus)
            i += self.stim_seq_length
        print(stimuli)
        print("================================")
        return stimuli
    
    def reset(self):
        pass