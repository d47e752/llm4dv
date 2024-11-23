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

from async_fifo.shared_types import *

wclk_period = 10
rclk_period = 13

PRECISION_COUNT = 1

class CoverageMonitor:

    def __init__(self):
        self.coverage_database = CoverageDatabase()
        self.coverage_database.misc_bins= {
            "full_read_wrap": 0,
            "gray_read_wrap": 0,
            "full_write_wrap": 0,
            "gray_write_wrap":0,
            "underflow": 0,
            "overflow": 0,
            "full": 0,
            "empty": 0,
            "read_while_write": 0,
            "write_while_read": 0
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

        self.clock_rising_edge = Event()

        # Read side monitoring
        self.rptr = None
        self.rptr_prev = None
        self.rempty_prev = None
        # Write side monitoring
        self.wptr = None
        self.wptr_prev = None
        self.wfull_prev = None

    # Handles driving a new_value when one is provided by `determine_next_value`
    async def controller_loop(self):
        await cocotb.start(read_monitor(self))
        await cocotb.start(write_monitor(self))
        with self.zmq_context.socket(zmq.REP) as socket:
            socket.bind(self.zmq_addr)

            while True:
                stimulus_msg = socket.recv()
                stimulus_obj = pickle.loads(stimulus_msg)
                print(stimulus_obj)

                dut_state = self.sample_dut_state()
                wait_time = stimulus_obj.value[0]
                read = stimulus_obj.value[1]
                write = stimulus_obj.value[2]

                winc = 0
                rinc = 0
                wdata = 0

                if read:
                    rinc = 1
                if write:
                    winc = 1

                self.dut.winc.value = winc
                self.dut.rinc.value = rinc
                self.dut.wdata.value = wdata

                await Timer(wait_time, units="ns")

                self.sample_signals()

                socket.send_pyobj((dut_state, self.coverage_monitor.coverage_database))

                if stimulus_obj.finish:
                    self.end_simulation_event.set()
                    break
    
    def check_hits(self):
        if(self.dut.rempty.value and not (self.rempty_prev == 1 or self.rempty_prev == None)):
            self.coverage_monitor.coverage_database.misc_bins["empty"] += 1
        if(self.dut.wfull.value and not (self.wfull_prev == 1 or self.wfull_prev == None)):
            self.coverage_monitor.coverage_database.misc_bins["full"] += 1
        if(self.dut.rptr.value == 0 and not (self.rptr_prev == 0 or self.rptr_prev == 1 or self.rptr_prev == None)):
            self.coverage_monitor.coverage_database.misc_bins["read_wrap"] += 1
        if(self.dut.wptr.value == 0 and not (self.wptr_prev == 0 or self.wptr_prev == 1 or self.wptr_prev == None)):
            self.coverage_monitor.coverage_database.misc_bins["write_wrap"] += 1

    def sample_signals(self):
        print("==========================")
        print("rptr: " + str(self.dut.rptr.value))
        print("wptr: " + str(self.dut.wptr.value))
        print("--------------------------")
        print("rempty: " + str(self.dut.rempty.value))
        print("arempty: " + str(self.dut.arempty.value))
        print("wfull: " + str(self.dut.wfull.value))
        print("awfull: " + str(self.dut.awfull.value))

    def sample_dut_state(self):
        return DUTState(
        )
    
    def close(self):
        self.zmq_context.term()

    def run_controller(self):
        cocotb.start_soon(self.controller_loop())

async def read_monitor(simulation_controller):
    while(not simulation_controller.end_simulation_event.is_set()):
        await RisingEdge(simulation_controller.dut.rclk)
        simulation_controller.clock_rising_edge.set()
        # if(not self.rptr == self.dut.rptr.value):
        simulation_controller.rptr_prev = simulation_controller.rptr
        simulation_controller.rptr = simulation_controller.dut.rptr.value
        if(simulation_controller.dut.rempty.value and not (simulation_controller.rempty_prev == 1 or simulation_controller.rempty_prev == None)):
            simulation_controller.coverage_monitor.coverage_database.misc_bins["empty"] += 1
        if(simulation_controller.rptr == 0 and not (simulation_controller.rptr_prev == 0 or simulation_controller.rptr_prev == 1 or simulation_controller.rptr_prev == None)):
            simulation_controller.coverage_monitor.coverage_database.misc_bins["full_read_wrap"] += 1
        if(str(simulation_controller.rptr)[0] != str(simulation_controller.rptr_prev)[0] and not simulation_controller.rptr_prev == None):
            simulation_controller.coverage_monitor.coverage_database.misc_bins["gray_read_wrap"] += 1
        if(simulation_controller.dut.rinc.value and simulation_controller.rempty_prev):
            simulation_controller.coverage_monitor.coverage_database.misc_bins["underflow"] += 1
        if(simulation_controller.dut.rinc.value and simulation_controller.dut.winc.value):
            simulation_controller.coverage_monitor.coverage_database.misc_bins["read_while_write"] += 1
        simulation_controller.rempty_prev = simulation_controller.dut.rempty.value

async def write_monitor(simulation_controller):
    while(not simulation_controller.end_simulation_event.is_set()):
        await RisingEdge(simulation_controller.dut.wclk)
        simulation_controller.clock_rising_edge.set()
        # if(not self.wptr == self.dut.wptr.value):
        simulation_controller.wptr_prev = simulation_controller.wptr
        simulation_controller.wptr = simulation_controller.dut.wptr.value
        if(simulation_controller.dut.wfull.value and not (simulation_controller.wfull_prev == 1 or simulation_controller.wfull_prev == None)):
            simulation_controller.coverage_monitor.coverage_database.misc_bins["full"] += 1
        if(simulation_controller.wptr == 0 and not (simulation_controller.wptr_prev == 0 or simulation_controller.wptr_prev == 1 or simulation_controller.wptr_prev == None)):
            simulation_controller.coverage_monitor.coverage_database.misc_bins["full_write_wrap"] += 1
        if(str(simulation_controller.wptr)[0] != str(simulation_controller.wptr_prev)[0] and not simulation_controller.wptr_prev == None):
            simulation_controller.coverage_monitor.coverage_database.misc_bins["gray_write_wrap"] += 1
        if(simulation_controller.dut.winc.value and simulation_controller.wfull_prev):
            simulation_controller.coverage_monitor.coverage_database.misc_bins["overflow"] += 1
        if(simulation_controller.dut.rinc.value and simulation_controller.dut.winc.value):
            simulation_controller.coverage_monitor.coverage_database.misc_bins["write_while_read"] += 1
        simulation_controller.wfull_prev = simulation_controller.dut.wfull.value

async def do_reset(dut):
    dut.rrst_n.value = 1
    dut.wrst_n.value = 1
    await ClockCycles(dut.wclk, 3)
    await ClockCycles(dut.rclk, 3)

    dut.rrst_n.value = 0
    dut.wrst_n.value = 0
    await ClockCycles(dut.wclk, 3)
    await ClockCycles(dut.rclk, 3)

    dut.rrst_n.value = 1
    dut.wrst_n.value = 1

@cocotb.test()
async def basic_test(dut):
    from global_shared_types import GlobalCoverageDatabase

    server_port = input("Please enter server's port (e.g. 5050, 5555): ")
    # server_port = "5050"

    trial_cnt = 0

    while True:
        trial_cnt += 1

        coverage_monitor = CoverageMonitor()
        cocotb.start_soon(Clock(dut.wclk, wclk_period, units="ns").start())
        cocotb.start_soon(Clock(dut.rclk, rclk_period, units="ns").start())

        await do_reset(dut)

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