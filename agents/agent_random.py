# Copyright ***
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

from agents.agent_base import *
import random


class RandomAgent(BaseAgent):
    def __init__(self, total_cycle=1000000, seed=0):
        super().__init__()
        self.seed = seed
        random.seed(self.seed)
        self.total_cycle = total_cycle
        self.current_cycle = 0

    def end_simulation(
        self, dut_state: GlobalDUTState, coverage_database: GlobalCoverageDatabase
    ):
        return not self.current_cycle < self.total_cycle

    def reset(self):
        self.current_cycle = 0

    def generate_next_value(
        self, dut_state: GlobalDUTState, coverage_database: GlobalCoverageDatabase
    ):
        if self.current_cycle % 10000 == 0:
            print(f"Generated {self.current_cycle} stimuli\n")
        self.current_cycle += 1
        return random.getrandbits(32)


class RandomAgent4IC(RandomAgent):
    def __init__(self, total_cycle=1000000, seed=0):
        super().__init__(total_cycle=total_cycle, seed=0)

    def generate_next_value(
        self, dut_state: GlobalDUTState, coverage_database: GlobalCoverageDatabase
    ):
        addr = int(dut_state.get_pc(), 16)
        instr = random.getrandbits(32)

        if self.current_cycle % 10000 == 0:
            print(f"Generated {self.current_cycle} stimuli\n")
        self.current_cycle += 1

        return [(addr, instr)]
    
class RandomAgent4AG_WB(RandomAgent):
    def __init__(self, total_cycle=1000000, seed=0):
        super().__init__(total_cycle=total_cycle, seed=0)

    def generate_next_value(
        self, dut_state: GlobalDUTState, coverage_database: GlobalCoverageDatabase
    ):
        in_features = random.getrandbits(6)
        out_features = random.getrandbits(6)

        if self.current_cycle % 10000 == 0:
            print(f"Generated {self.current_cycle} stimuli\n")
        self.current_cycle += 1

        return [in_features, out_features]
    
class RandomAgent4AG_FT(RandomAgent):
    def __init__(self, total_cycle=1000000, seed=0):
        super().__init__(total_cycle=total_cycle, seed=0)

    def generate_next_value(
        self, dut_state: GlobalDUTState, coverage_database: GlobalCoverageDatabase
    ):
        op = random.randint(0, 4)
        nodeslot = random.getrandbits(6)
        feature_count = random.getrandbits(10)
        neighbour_count = random.getrandbits(10)

        if(op == 0):
            op = "deallocate"
        elif(op==1):
            op = "allocate"
        elif(op==2):
            op = "adjacency_write"
        elif(op==3):
            op = "message_write"
        elif(op==4):
            op = "scale_write"

        if self.current_cycle % 10000 == 0:
            print(f"Generated {self.current_cycle} stimuli\n")
        self.current_cycle += 1


        return [op, nodeslot, feature_count, neighbour_count]
    
class RandomAgent4AF(RandomAgent):
    def __init__(self, total_cycle=1000000, seed=0):
        super().__init__(total_cycle=total_cycle, seed=0)

    def generate_next_value(
        self, dut_state: GlobalDUTState, coverage_database: GlobalCoverageDatabase
    ):
        wait_time = random.getrandbits(10)
        read = random.getrandbits(1)
        write = random.getrandbits(1)

        if self.current_cycle % 10000 == 0:
            print(f"Generated {self.current_cycle} stimuli\n")
        self.current_cycle += 1

        return [wait_time, read, write]
    
class RandomAgent4SDRAM(RandomAgent):
    def __init__(self, total_cycle=1000000, seed=0):
        super().__init__(total_cycle=total_cycle, seed=0)

    def generate_next_value(
        self, dut_state: GlobalDUTState, coverage_database: GlobalCoverageDatabase
    ):
        wr_enable = random.getrandbits(1)
        rd_enable = random.getrandbits(1)
        reset = random.getrandbits(1)

        if self.current_cycle % 10000 == 0:
            print(f"Generated {self.current_cycle} stimuli\n")
        self.current_cycle += 1

        return [wr_enable, rd_enable, reset]
    
class RandomAgent4MIPS(RandomAgent):
    def __init__(self, total_cycle=1000000, seed=0):
        super().__init__(total_cycle=total_cycle, seed=0)

    def generate_next_value(
        self, dut_state: GlobalDUTState, coverage_database: GlobalCoverageDatabase
    ):
        instr = random.getrandbits(32)

        if self.current_cycle % 1000 == 0:
            print(f"Generated {self.current_cycle} stimuli\n")
        self.current_cycle += 1

        return [instr]
