import sys
import os

import zmq
import pickle
from contextlib import closing

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, ClockCycles, ReadWrite, Event, RisingEdge

directory = os.path.dirname(os.path.abspath("__file__"))
sys.path.insert(0, os.path.dirname("/".join(directory.split("/")[:-1])))

from agile_prefetcher.weight_bank.shared_types import *
from shared_helpers.cocotb_helpers import *

AG_WB_BOUND = 64

class CoverageMonitor:

    def __init__(self, dut):
        self.coverage_database = CoverageDatabase()
        self.coverage_database.in_features = [0]*(int(AG_WB_BOUND/16+1))
        self.coverage_database.out_features = [0]*(AG_WB_BOUND+1)
        self.coverage_database.combined_features = [[0] * (AG_WB_BOUND+1) for _ in range(int(AG_WB_BOUND/16+1))]
        self.coverage_sampled_event = Event()

        self.max_high = 0
        self.duration = 0

# Produces the stimulus for the testbench based on observed coverage
class SimulationController:
    def __init__(self, dut, coverage_monitor, zmq_addr):
        self.dut = dut
        self.coverage_monitor = coverage_monitor
        self.end_simulation_event = Event()
        self.zmq_context = zmq.Context()
        self.zmq_addr = zmq_addr
        self.continue_sampling = False

    # Handles driving a new_value when one is provided by `determine_next_value`
    async def controller_loop(self):
        with self.zmq_context.socket(zmq.REP) as socket:
            socket.bind(self.zmq_addr)

            await ClockCycles(self.dut.core_clk, 1)
            await ReadWrite()

            while True:
                stimulus_msg = socket.recv()
                await do_reset(reset_sig=self.dut.resetn, clock_sig=self.dut.core_clk, reset_cycles=3) # needs reset for every new stimulus due to possible state machine issue
                stimulus_obj = pickle.loads(stimulus_msg)
                print(stimulus_obj)

                if not isinstance(stimulus_obj, Stimulus):
                    assert False, "Saw bad stimulus message"

                dut_state = self.sample_dut_state()

                # drive primary input
                if(int(self.dut.nsb_prefetcher_weight_bank_req_ready.value) == 0):
                    await RisingEdge(self.dut.nsb_prefetcher_weight_bank_req_ready) # wait until dut can receive request
                if stimulus_obj.value is None:
                    self.dut.nsb_prefetcher_weight_bank_req_valid.value = 0
                    self.dut.nsb_prefetcher_weight_bank_req.value = 0
                else:
                    req_opcode = 0
                    start_address = 0
                    in_features = int(stimulus_obj.value[0])
                    if(in_features < 1):
                        in_features = 1
                    out_features = int(stimulus_obj.value[1])
                    if(out_features < 1):
                        out_features = 1
                    nodeslot = 0
                    nodeslot_precision = 0
                    neighbour_count = 0

                    payload = assemble_payload_from_struct([
                        [neighbour_count, 10],
                        [nodeslot_precision, 2],
                        [nodeslot, 6],
                        [out_features, 11],
                        [in_features, 11],
                        [start_address, 34],
                        [req_opcode, 3]])

                    self.dut.nsb_prefetcher_weight_bank_req_valid.value = 1
                    self.dut.nsb_prefetcher_weight_bank_req.value = payload

                if(int(self.dut.weight_channel_resp_valid.value) == 0):
                    await RisingEdge(self.dut.weight_channel_resp_valid)
                cont = True
                while(cont):
                    valid_mask = str(self.dut.weight_channel_resp)[-1024:-1]
                    number_of_ones = valid_mask.count('1')
                    cont = number_of_ones == 0
                    await ClockCycles(self.dut.core_clk, 1)
                self.continue_sampling = True
                while (self.continue_sampling):
                    self.continue_sampling = determine_coverage(
                        coverage_monitor=self.coverage_monitor, 
                        sample_condition=self.dut.weight_channel_resp_ready.value and self.dut.weight_channel_resp_valid.value,
                        signals=str(self.dut.weight_channel_resp)[-1024:-1],
                        finish_condition=str(self.dut.weight_channel_resp)[-1] == '1',
                        duration=[self.coverage_monitor.coverage_database.in_features, 16, -1],
                        count_high=[1,self.coverage_monitor.coverage_database.out_features],
                        combine=[0,self.coverage_monitor.coverage_database.combined_features]
                        )
                    await ClockCycles(self.dut.core_clk, 1)

                socket.send_pyobj((dut_state, self.coverage_monitor.coverage_database))

                if stimulus_obj.finish:
                    self.end_simulation_event.set()
                    break

    def sample_dut_state(self):
        return DUTState(
            reset_weights=int(self.dut.reset_weights.value),
        )
    
    def close(self):
        self.zmq_context.term()

    def run_controller(self):
        cocotb.start_soon(self.controller_loop())

@cocotb.test()
async def basic_test(dut):
    from global_shared_types import GlobalCoverageDatabase

    server_port = input("Please enter server's port (e.g. 5050, 5555): ")
    # server_port = "5050"

    trial_cnt = 0

    while True:
        trial_cnt += 1

        coverage_monitor = CoverageMonitor(dut)
        cocotb.start_soon(Clock(dut.core_clk, 10, units="ns").start())

        # force unused signals
        dut.weight_bank_axi_rm_fetch_req_ready.value = 1
        dut.weight_bank_axi_rm_fetch_resp_valid.value = 1
        dut.weight_bank_axi_rm_fetch_resp_last.value = 0
        dut.weight_bank_axi_rm_fetch_resp_data.value = 0
        dut.weight_bank_axi_rm_fetch_resp_axi_id.value = 0
        dut.weight_channel_req_valid.value = 1
        dut.weight_channel_req.value = 0
        dut.weight_channel_resp_ready.value = 1
        dut.layer_config_weights_address_lsb_value.value = 0

        await do_reset(reset_sig=dut.resetn, clock_sig=dut.core_clk, reset_cycles=3)

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