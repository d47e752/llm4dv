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
sys.path.insert(0, os.path.dirname("/".join(directory.split("/")[:-1])))

from agile_prefetcher.fetch_tag.shared_types import *
from shared_helpers.cocotb_helpers import *

PRECISION_COUNT = 1

class CoverageMonitor:

    def __init__(self):
        self.coverage_database = CoverageDatabase()
        self.coverage_database.misc_bins= {
            "adjacency_list_partial": 0,
            "adjacency_list_nopartial": 0,

            "messages_partial": 0,
            "messages_nopartial": 0,

            "scale_factor_partial": 0,
            "scale_factor_nopartial":0
        }
        
        for precision in range(PRECISION_COUNT):
            self.coverage_database.misc_bins["weights_" + precision] = 0

        self.coverage_sampled_event = Event()

# Produces the stimulus for the testbench based on observed coverage
class SimulationController:
    def __init__(self, dut, coverage_monitor, zmq_addr):
        self.dut = dut
        self.coverage_monitor = coverage_monitor
        self.end_simulation_event = Event()
        self.zmq_context = zmq.Context()
        self.zmq_addr = zmq_addr

        self.tag_allocated = False

    # Handles driving a new_value when one is provided by `determine_next_value`
    async def controller_loop(self):
        with self.zmq_context.socket(zmq.REP) as socket:
            socket.bind(self.zmq_addr)

            await ClockCycles(self.dut.core_clk, 1)
            await ReadWrite()

            while True:
                stimulus_msg = socket.recv()
                stimulus_obj = pickle.loads(stimulus_msg)
                print(stimulus_obj)

                dut_state = self.sample_dut_state()

                if(not self.dut.nsb_prefetcher_req_ready.value):
                    await RisingEdge(self.dut.nsb_prefetcher_req_ready.value)

                stimulus = stimulus_obj.value
                req_opcode = stimulus[0]
                start_address = stimulus[1]
                in_features = stimulus[2]
                out_features = stimulus[3]
                nodeslot = stimulus[4]
                nodeslot_precision = stimulus[5]
                neighbour_count = stimulus[6]

                payload_nsb_prefetcher_req = assemble_payload_from_struct([
                    [neighbour_count, 10],
                    [nodeslot_precision, 2],
                    [nodeslot, 6],
                    [out_features, 11],
                    [in_features, 11],
                    [start_address, 34],
                    [req_opcode, 3]])
                
                self.dut.nsb_prefetcher_req.value = payload_nsb_prefetcher_req

                timeout = False
                cycle_count = 0

                while(not self.dut.nsb_prefetcher_resp_valid.value):
                    cycle_count += 1
                    if cycle_count > 1000:
                        timeout = True
                        print("No valid response has been received")
                        break
                    await ClockCycles(self.dut.core_clk, 1)
                
                if(not timeout):
                    self.check_hits(self.dut.nsb_prefetcher_resp.value)
                
                socket.send_pyobj((dut_state, self.coverage_monitor.coverage_database))

                if stimulus_obj.finish:
                    self.end_simulation_event.set()
                    break
    
    def check_hits(self, response):
        partial = self.dut.nsb_prefetcher_resp.value[0]
        allocated_fetch_tag = self.dut.nsb_prefetcher_resp.value[1:7]
        response_type = self.dut.nsb_prefetcher_resp.value[8:11]
        nodeslot = self.dut.nsb_prefetcher_resp.value[12:]

        if(response_type == 0):
            instruction_type = "weights"
            precision = str(int(self.dut.active_weight_fetch_precision.value))
            self.coverage_monitor["weights_" + precision] += 1
        else:
            if(response_type == 1):
                instruction_type = "adjacency_list"
            elif(response_type == 2):
                instruction_type = "messages"
            elif(response_type == 3):
                instruction_type = "scale_factor"
            if(partial):
                self.coverage_monitor[instruction_type + "_partial"] += 1
            else:
                self.coverage_monitor[instruction_type + "_nopartial"] += 1
        return

    def sample_dut_state(self):
        return DUTState(
            allocated_nodeslot=int(self.dut.allocated_nodeslot.value),
        )
    
    def close(self):
        self.zmq_context.term()

    def run_controller(self):
        cocotb.start_soon(self.controller_loop())

    def sample_signals(self):
            # sample important signals
            print("===================")
            print("Tag free: " + str(self.dut.tag_free))
            print("ADJ Q empty: " + str(self.dut.adj_queue_empty))
            
            print("Message fetch state: " + str(self.dut.message_fetch_state.value))
            print("Adj queue slots available: " + str(self.dut.adj_queue_slots_available.value))
            print("Message queue slots count: " + str(self.dut.message_queue_count.value))
            print("Message SM next state " + str(self.dut.message_fetch_state_n.value))

            print("Byte count: " + str(self.dut.fetch_tag_msg_rm_byte_count.value))
            print("Scale factor request valid: " + str(self.dut.scale_factor_read_master_req_valid.value))
            print("Expected responses: " + str(self.dut.msg_queue_expected_responses.value))

            print("NSB response valid: " + str(self.dut.nsb_prefetcher_resp_valid.value))
            print("Message channel response valid: " + str(self.dut.message_channel_resp_valid.value))
            print("Message channel last_feature: " + str(self.dut.message_channel_resp.value[-1]))
            print("Message channel last_neighbour: " + str(self.dut.message_channel_resp.value[-2]))

            print("Adj done: " + str(self.dut.adj_queue_fetch_resp_valid.value))

            print("Message queue full: " + str(self.dut.message_queue_full.value))
            return


@cocotb.test()
async def basic_test(dut):
    from global_shared_types import GlobalCoverageDatabase

    server_port = input("Please enter server's port (e.g. 5050, 5555): ")

    trial_cnt = 0

    while True:
        trial_cnt += 1

        coverage_monitor = CoverageMonitor()
        cocotb.start_soon(Clock(dut.core_clk, 10, units="ns").start())

        # force unimportant signals
        dut.nsb_prefetcher_req_valid

        # Register Bank
        dut.s_axi_awaddr
        dut.s_axi_awprot
        dut.s_axi_awvalid
        dut.s_axi_wdata
        dut.s_axi_wstrb
        dut.s_axi_wvalid
        dut.s_axi_araddr
        dut.s_axi_arprot
        dut.s_axi_arvalid
        dut.s_axi_rready
        dut.s_axi_bready

        # Prefetcher Adjacency Read Master -> AXI Memory Interconnect
        dut.prefetcher_adj_rm_axi_interconnect_axi_arready
        dut.prefetcher_adj_rm_axi_interconnect_axi_awready
        dut.prefetcher_adj_rm_axi_interconnect_axi_bid
        dut.prefetcher_adj_rm_axi_interconnect_axi_bresp
        dut.prefetcher_adj_rm_axi_interconnect_axi_bvalid
        dut.prefetcher_adj_rm_axi_interconnect_axi_rdata
        dut.prefetcher_adj_rm_axi_interconnect_axi_rid
        dut.prefetcher_adj_rm_axi_interconnect_axi_rlast
        dut.prefetcher_adj_rm_axi_interconnect_axi_rresp
        dut.prefetcher_adj_rm_axi_interconnect_axi_rvalid
        dut.prefetcher_adj_rm_axi_interconnect_axi_wready

        # Prefetcher Message Read Master -> AXI Memory Interconnect
        dut.prefetcher_msg_rm_axi_interconnect_axi_arready
        dut.prefetcher_msg_rm_axi_interconnect_axi_awready
        dut.prefetcher_msg_rm_axi_interconnect_axi_bid
        dut.prefetcher_msg_rm_axi_interconnect_axi_bresp
        dut.prefetcher_msg_rm_axi_interconnect_axi_bvalid
        dut.prefetcher_msg_rm_axi_interconnect_axi_rdata
        dut.prefetcher_msg_rm_axi_interconnect_axi_rid
        dut.prefetcher_msg_rm_axi_interconnect_axi_rlast
        dut.prefetcher_msg_rm_axi_interconnect_axi_rresp
        dut.prefetcher_msg_rm_axi_interconnect_axi_rvalid
        dut.prefetcher_msg_rm_axi_interconnect_axi_wready

        # Prefetcher Weight Bank Read Master -> AXI Memory Interconnect
        dut.prefetcher_weight_bank_rm_axi_interconnect_axi_arready
        dut.prefetcher_weight_bank_rm_axi_interconnect_axi_awready
        dut.prefetcher_weight_bank_rm_axi_interconnect_axi_bid
        dut.prefetcher_weight_bank_rm_axi_interconnect_axi_bresp
        dut.prefetcher_weight_bank_rm_axi_interconnect_axi_bvalid
        dut.prefetcher_weight_bank_rm_axi_interconnect_axi_rdata
        dut.prefetcher_weight_bank_rm_axi_interconnect_axi_rid
        dut.prefetcher_weight_bank_rm_axi_interconnect_axi_rlast
        dut.prefetcher_weight_bank_rm_axi_interconnect_axi_rresp
        dut.prefetcher_weight_bank_rm_axi_interconnect_axi_rvalid
        dut.prefetcher_weight_bank_rm_axi_interconnect_axi_wready

        # Message Channels: AGE -> Prefetcher Feature Bank
        dut.message_channel_req_valid
        dut.message_channel_req
        dut.message_channel_resp_ready
        
        # Weight Channels: FTE -> Prefetcher Weight Bank
        dut.weight_channel_req_valid
        dut.weight_channel_req
        dut.weight_channel_resp_ready
        dut.scale_factor_queue_pop

        await do_reset(dut.resetn, dut.core_clk, 3)

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

# nsb_prefetcher_req MAIN INPUT
# nsb_prefetcher_resp RESPONSE