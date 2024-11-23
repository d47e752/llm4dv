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

class CoverageMonitor:

    def __init__(self):
        self.coverage_database = CoverageDatabase()
        self.coverage_database.misc_bins= {
            "adj_dealloc": 0,
            "mess_dealloc": 0,
            "scale_dealloc": 0,

            "adj_nomatch": 0,
            "mess_nomatch": 0,
            "scale_nomatch": 0,

            "mess_fetch_adj_nopartial": 0,
            "mess_fetch_adj_partial": 0,
            
            "mess_seen": 0,

            "scale_seen": 0,
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

                stimulus = stimulus_obj.value
                op = stimulus[0]
                op = op.lower()
                nodeslot = stimulus[1]
                feature_count = stimulus[2]
                neighbour_count = stimulus[3]

                if(op == "deallocate"):
                    await self.deallocate_tag()
                elif(op == "allocate"):
                    await self.allocate_tag(nodeslot=nodeslot,feature_count=feature_count)
                elif(op == "adjacency_write"):
                    await self.req_adj_write(neighbour_count=neighbour_count, nodeslot=nodeslot)
                # elif(op == "adjacency_read"):
                #     await self.req_adj_read()
                elif(op == "message_write"):
                    await self.req_message_write(nodeslot=nodeslot)
                # elif(op == "message_read"):
                #     await self.req_message_read(nodeslot=nodeslot)
                elif(op == "scale_write"):
                    await self.req_scale_write(neighbour_count=neighbour_count, nodeslot=nodeslot)
                # elif(op == "scale_read"):
                #     await self.req_scale_read()

                socket.send_pyobj((dut_state, self.coverage_monitor.coverage_database))

                if stimulus_obj.finish:
                    self.end_simulation_event.set()
                    break

    # allocate fetch tag
    async def allocate_tag(self, nodeslot, feature_count):
        print("==================================")
        print("Allocating tag")
        print("Nodeslot:" + str(nodeslot))
        print("Feature count: " + str(feature_count))        
        self.dut.allocation_valid.value = 1
        self.dut.allocation_nodeslot.value = nodeslot
        self.dut.allocation_feature_count.value = feature_count
        await ClockCycles(self.dut.core_clk, 1)
        self.dut.allocation_valid.value = 0
        self.tag_allocated = True
    
    async def deallocate_tag(self):
        print("==================================")
        print("Deallocating tag")
        self.dut.deallocation_valid.value = 1
        await ClockCycles(self.dut.core_clk, 1)
        self.dut.deallocation_valid.value = 0
        self.tag_allocated = False
         
    
    async def req_adj_write(self, neighbour_count, nodeslot):

        print("==================================")
        print("Filling adjacency queue")
        print("Nodeslot:" + str(nodeslot))
        print("Neighbour count: " + str(neighbour_count))

        self.dut.nsb_prefetcher_req_valid.value = 1

        nodeslot_precision = 0
        out_features = 0
        in_features = 0
        start_address = 0
        req_opcode = 1

        payload_nsb_prefetcher_req = assemble_payload_from_struct([
            [neighbour_count, 10],
            [nodeslot_precision, 2],
            [nodeslot, 6],
            [out_features, 11],
            [in_features, 11],
            [start_address, 34],
            [req_opcode, 3]])

        self.dut.nsb_prefetcher_req.value = payload_nsb_prefetcher_req

        if(not self.tag_allocated):
            self.coverage_monitor.coverage_database.misc_bins["adj_dealloc"] += 1
            await ClockCycles(self.dut.core_clk, 1)
            return
        elif(self.dut.allocated_nodeslot.value != nodeslot):
            self.coverage_monitor.coverage_database.misc_bins["adj_nomatch"] += 1
            await ClockCycles(self.dut.core_clk, 1)
            return
        else:
            while (self.dut.adj_queue_fetch_resp_valid.value == 0 and self.dut.adj_queue_manager_i.issue_partial_done.value[0] == 0 and self.dut.adj_queue_full.value == 0 and self.dut.adj_queue_manager_i.fetch_state.value != 0):
                self.sample_signals()
                await ClockCycles(self.dut.core_clk, 1)

        self.dut.nsb_prefetcher_req_valid.value = 0
    
    async def req_adj_read(self):
        print("==================================")
        print("Reading adjacency queue info")
        adj_count = self.dut.adj_queue_count.value
        adj_partial = self.dut.adj_queue_manager_i.issue_partial_done.value[0]
        print("Count: " + str(adj_count))
        print("Partial: " + str(adj_partial))

    async def req_message_write(self, nodeslot):
        if(self.dut.adj_queue_manager_i.issue_partial_done.value[0] == 1):
            self.coverage_monitor.coverage_database.misc_bins["mess_fetch_adj_nopartial"] += 1
        else:
            self.coverage_monitor.coverage_database.misc_bins["mess_fetch_adj_partial"] += 1
        
        print("==================================")
        print("Filling message queue")
        print("Nodeslot:" + str(nodeslot))
        self.dut.nsb_prefetcher_req_valid.value = 1

        neighbour_count = 0
        nodeslot_precision = 0
        out_features = 0
        in_features = 0
        start_address = 0
        req_opcode = 2


        payload_nsb_prefetcher_req = assemble_payload_from_struct([
            [neighbour_count, 10],
            [nodeslot_precision, 2],
            [nodeslot, 6],
            [out_features, 11],
            [in_features, 11],
            [start_address, 34],
            [req_opcode, 3]])

        self.dut.nsb_prefetcher_req.value = payload_nsb_prefetcher_req

        await ClockCycles(self.dut.core_clk, 1)
        
        if(not self.tag_allocated):
            self.coverage_monitor.coverage_database.misc_bins["mess_dealloc"] += 1
            return
        if(self.dut.allocated_nodeslot.value != nodeslot):
            self.coverage_monitor.coverage_database.misc_bins["mess_nomatch"] += 1
            return
        else:
            if(self.dut.message_fetch_state_n.value == 0):
                print("No messages have been written.")
            else:
                while (self.dut.trigger_msg_partial_resp.value == 0 and self.dut.message_fetch_state.value != 4 and self.dut.message_queue_full.value == 0):
                    self.sample_signals()
                    await ClockCycles(self.dut.core_clk, 1)
            self.coverage_monitor.coverage_database.misc_bins["mess_seen"] += 1
            self.dut.nsb_prefetcher_req_valid.value = 0
    
    async def req_message_read(self, nodeslot):
        print("==================================")
        print("Reading message queue info")
        print("Nodeslot:" + str(nodeslot))

        fetch_tag = 0

        payload_message_channel_req = assemble_payload_from_struct([fetch_tag,7],[nodeslot,7])

        self.dut.message_channel_req.value = payload_message_channel_req
        await ClockCycles(self.dut.core_clk, 1)
        
        if (self.dut.message_channel_req_ready.value == 1):
            self.dut.nsb_prefetcher_req_valid.value = 1
        else:
            print("Message channel request not ready!")
            return

        messages_count = 1
        one_neighbour_count = 1
        while(not(self.dut.message_channel_resp_valid.value == 1 and self.dut.message_channel_resp.value[-1] == 1)):
            if(self.dut.message_channel_resp_valid.value):
                messages_count += 1
                if(self.dut.message_channel_resp.value[-2] == 1):
                    one_neighbour_count += 1
            self.sample_signals()
            await ClockCycles(self.dut.core_clk, 1)
        self.dut.nsb_prefetcher_req_valid.value = 0
        print("Number of messages received: " + str(messages_count))
        print("Last neighbour message count: " + str(one_neighbour_count))

    
    async def req_scale_write(self, neighbour_count, nodeslot):
        print("==================================")
        print("Filling scale queue")
        print("Nodeslot:" + str(nodeslot))
        print("Neighbour count: " + str(neighbour_count))

        self.dut.nsb_prefetcher_req_valid.value = 1
        nodeslot_precision = 0
        out_features = 0
        in_features = 0
        start_address = 0
        req_opcode = 3
        
        payload_nsb_prefetcher_req = assemble_payload_from_struct([
            [neighbour_count, 10],
            [nodeslot_precision, 2],
            [nodeslot, 6],
            [out_features, 11],
            [in_features, 11],
            [start_address, 34],
            [req_opcode, 3]])

        self.dut.nsb_prefetcher_req.value = payload_nsb_prefetcher_req

        if(not self.tag_allocated):
            self.coverage_monitor.coverage_database.misc_bins["scale_dealloc"] += 1
            await ClockCycles(self.dut.core_clk, 1)
            return
        elif(self.dut.allocated_nodeslot.value != nodeslot):
            self.coverage_monitor.coverage_database.misc_bins["scale_nomatch"] += 1
            await ClockCycles(self.dut.core_clk, 1)
            return
        else:
            while (self.dut.scale_factor_fetch_resp_valid.value == 0 and self.dut.scale_factor_queue_manager.issue_partial_done.value[0] == 0 and self.dut.scale_factor_queue_full.value == 0 and self.dut.scale_factor_queue_manager.fetch_state.value != 0):
                await ClockCycles(self.dut.core_clk, 1)
                self.sample_signals()
            self.coverage_monitor.coverage_database.misc_bins["scale_seen"] += 1

            print("------------------")
            print(self.dut.scale_factor_queue_count.value)
            print("------------------")

        self.dut.nsb_prefetcher_req_valid.value = 0
    
    async def req_scale_read(self):
        print("==================================")
        print("Reading scale queue info")
        pop_count = 0
        while(self.dut.scale_factor_queue_empty.value != 1):
            if(self.dut.scale_factor_queue_out_valid.value == 1):
                self.dut.scale_factor_queue_pop.value = 1
                pop_count += 1
            else:
                self.dut.scale_factor_queue_pop.value = 0
            self.sample_signals()
            await ClockCycles(self.dut.core_clk, 1)
        print("Scale queue count: " + str(pop_count))
        
    
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
    # server_port = "5050"
    trial_cnt = 0

    while True:
        trial_cnt += 1

        coverage_monitor = CoverageMonitor()
        cocotb.start_soon(Clock(dut.core_clk, 10, units="ns").start())

        # force unimportant signals
        dut.nsb_prefetcher_req_valid.value = 1
        dut.nsb_prefetcher_resp_ready.value = 1
        dut.fetch_tag_adj_rm_req_ready.value = 1
        dut.fetch_tag_adj_rm_resp_valid.value = 1
        dut.fetch_tag_adj_rm_resp_data.value = 0
        dut.fetch_tag_adj_rm_resp_axi_id.value = 0
        dut.fetch_tag_msg_rm_req_ready.value = 1
        dut.fetch_tag_msg_rm_resp_valid.value = 1
        dut.fetch_tag_msg_rm_resp_axi_id.value = 0
        dut.message_channel_req_valid.value = 1
        dut.message_channel_resp_ready.value = 1
        dut.fetch_tag_adj_rm_resp_last.value = 0
        dut.fetch_tag_msg_rm_resp_data.value = 0
        dut.scale_factor_queue_pop.value = 0
        dut.layer_config_adjacency_list_address_lsb_value.value = 0
        dut.layer_config_in_messages_address_lsb_value.value = 0
        dut.layer_config_scale_factors_address_lsb_value.value = 0
        dut.layer_config_scale_factors_address_msb_value.value = 0

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
        break