# scale_factor_queue_pop should be high?

import sys
import os

import random
import math

import functools
import zmq
import pickle
from contextlib import closing

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, ClockCycles, ReadWrite, ReadOnly, Event, RisingEdge

directory = os.path.dirname(os.path.abspath("__file__"))
sys.path.insert(0, os.path.dirname(directory))

from shared_helpers.cocotb_helpers import *
from sdram_controller.shared_types import *

class CoverageMonitor:

    def __init__(self):
        self.coverage_database = CoverageDatabase()
        self.coverage_database.misc_bins= {
            "precharge": 0,
            "auto_refresh": 0,
            "command_inhibit": 0,
            "load_mode_register":0,
            "activate": 0,
            "read": 0,
            "write": 0
        }

        self.coverage_sampled_event = Event()

# Produces the stimulus for the testbench based on observed coverage
class SimulationController:
    def __init__(self, dut, coverage_monitor, zmq_addr):
        self.dut = dut
        self.coverage_monitor = coverage_monitor
        self.end_simulation_event = Event()
        self.zmq_context = zmq.Context()
        self.zmq_addr = zmq_addr

    # Handles driving a new_value when one is provided by `determine_next_value`
    async def controller_loop(self):
        await cocotb.start(async_check_hits(self))
        with self.zmq_context.socket(zmq.REP) as socket:
            socket.bind(self.zmq_addr)

            while True:
                stimulus_msg = socket.recv()
                stimulus_obj = pickle.loads(stimulus_msg)
                print(stimulus_obj)

                dut_state = self.sample_dut_state()
                wr_enable = stimulus_obj.value[0]
                rd_enable = stimulus_obj.value[1]
                reset = stimulus_obj.value[2]

                while (self.dut.state_cnt.value != 0):
                    await ClockCycles(self.dut.clk, 1)

                if(reset):
                    reset_cycles = 3
                    self.dut.rst_n.value = 0
                    print("RESET")
                else:
                    reset_cycles = -1
                    self.dut.rst_n.value = 1

                self.dut.wr_enable.value = wr_enable
                self.dut.rd_enable.value = rd_enable

                print(self.dut.state.value)
                await ClockCycles(self.dut.clk, 1)
                while(self.dut.busy.value or reset_cycles > 0):
                    await ClockCycles(self.dut.clk, 1)
                    reset_cycles -= 1
                self.dut.rst_n.value = 1

                socket.send_pyobj((dut_state, self.coverage_monitor.coverage_database))

                if stimulus_obj.finish:
                    self.end_simulation_event.set()
                    break
    
    def check_hits(self):
        cs = self.dut.cs_n.value
        ras = self.dut.ras_n.value
        cas = self.dut.cas_n.value
        we = self.dut.we_n.value

        if(not cs and not ras and cas and not we):
            self.coverage_monitor.coverage_database.misc_bins["precharge"] += 1
        if(not cs and not ras and not cas and we):
            self.coverage_monitor.coverage_database.misc_bins["auto_refresh"] += 1
        if(not cs and ras and cas and we):
            self.coverage_monitor.coverage_database.misc_bins["command_inhibit"] += 1
        if(not cs and not ras and not cas and not we):
            self.coverage_monitor.coverage_database.misc_bins["load_mode_register"] += 1
        if(not cs and not ras and cas and we):
            self.coverage_monitor.coverage_database.misc_bins["activate"] += 1
        if(not cs and ras and not cas and we):
            self.coverage_monitor.coverage_database.misc_bins["read"] += 1
        if(not cs and ras and not cas and not we):
            self.coverage_monitor.coverage_database.misc_bins["write"] += 1


    def sample_dut_state(self):
        return DUTState(
        )
    
    def close(self):
        self.zmq_context.term()

    def run_controller(self):
        cocotb.start_soon(self.controller_loop())

async def async_check_hits(simulation_controller):
    while(not simulation_controller.end_simulation_event.is_set()):
        await RisingEdge(simulation_controller.dut.clk)
        simulation_controller.check_hits()

@cocotb.test()
async def basic_test(dut):
    from global_shared_types import GlobalCoverageDatabase

    # server_port = "5555"
    server_port = input("Please enter server's port (e.g. 5050, 5555): ")

    trial_cnt = 0

    while True:
        trial_cnt += 1

        coverage_monitor = CoverageMonitor()
        cocotb.start_soon(Clock(dut.clk, 100, units="ns").start())

        await do_reset(dut.rst_n, dut.clk, 3)

        with closing(
            SimulationController(dut, coverage_monitor, f"tcp://*:{server_port}")
        ) as simulation_controller:
            simulation_controller.run_controller()

            # Wait for end of simulation to be signalled. Give the design a few more
            # clocks to run before outputting final coverage values
            await simulation_controller.end_simulation_event.wait()
            await Timer(5, units="ns")

            print(f"***** FINAL COVERAGE of trial #{trial_cnt} *****")
            print(
                GlobalCoverageDatabase(
                    coverage_monitor.coverage_database
                ).get_coverage_rate()
            )
        break