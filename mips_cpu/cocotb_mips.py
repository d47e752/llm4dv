import struct
import zmq
import os
import sys

directory = os.path.dirname(os.path.abspath("__file__"))
sys.path.insert(0, os.path.dirname(directory))

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, ClockCycles, ReadWrite, Event
from mips_cpu.instruction_monitor import InstructionMonitor
from mips_cpu.shared_types import Stimulus, MipsStateInfo

from contextlib import closing

instr_buffer = []

async def do_reset(dut):
    dut.rst.value = 0
    await ClockCycles(dut.clk, 3)

    dut.rst.value = 1
    await ClockCycles(dut.clk, 3)

    dut.rst.value = 0
    while(dut.cpu_core_inst.instr_fetch_inst.bpu_inst.btb_inst.is_reseting.value):
        await ClockCycles(dut.clk, 1)

def debug(dut):
    print("==============================================================")
    print("PC: " + hex(dut.cpu_core_inst.instr_fetch_inst.pc_gen.pc.value))
    print("PC enable: " + str(dut.cpu_core_inst.instr_fetch_inst.pc_gen.pc_en.value))
    print("Reset: " + str(dut.rst.value))
    print("Is reseting: " + str(dut.cpu_core_inst.instr_fetch_inst.bpu_inst.btb_inst.is_reseting.value))
    print("IBUS read: " + str(dut.ibus_read.value))
    print("IBUS read address: " + hex(dut.ibus_address.value))
    print("IBUS data: " + hex(dut.ibus_rddata.value))
    print("IBUS valid: " + str(dut.ibus_valid.value))
    print("IBUS ready: " + str(dut.ibus_ready.value))
    print("---------------------------------------------------------------")


prog = [0x00000293, 0x01400313, 0x006282B3, 0xFFDFF06F]


class MemAgent:
    def __init__(self, dut, mem_name, default_load_val=0x00000000, handle_writes=True):
        self.mem_dict = {}

        self.clk = dut.clk
        self.req = getattr(dut, mem_name + "_read")
        self.addr = getattr(dut, mem_name + "_address")
        self.rdata = getattr(dut, mem_name + "_rddata")

        self.default_load_val = default_load_val

        self.handle_writes = handle_writes

        if handle_writes:
            self.we = getattr(dut, mem_name + "_write")
            self.wdata = getattr(dut, mem_name + "_wrdata")
            self.be = getattr(dut, mem_name + "_byteenable")
        else:
            self.rvalid = getattr(dut, mem_name + "_valid")
            self.rvalid_extra = getattr(dut, mem_name + "_extra_valid")

    def load_bin(self, bin_filename, start_addr):
        with open(bin_filename, "rb") as bin_file:
            cur_addr = start_addr

            for (word,) in struct.iter_unpack("<I", bin_file.read()):
                self.mem_dict[cur_addr] = word
                cur_addr += 4

    def write_mem(self, addr, word):
        self.mem_dict[addr] = word

    async def run_mem(self):
        global instr_buffer
        if(not self.handle_writes):
            self.rvalid.value = 1

        while True:
            await ClockCycles(self.clk, 1)
            await ReadWrite()

            if self.req.value:
                access_addr = self.addr.value

                if self.handle_writes and self.we.value:
                    write_data = self.wdata.value
                else:
                    write_data = None

                if self.handle_writes and write_data:
                    self.rdata.value = 0xDEADBAAD
                    self.mem_dict[int(access_addr)] = int(write_data)
                else:
                    if(len(instr_buffer) > 0):
                        self.rdata.value = instr_buffer[0]
                    else:
                        self.rdata.value = 0x0


async def update_magic_loc(dut, dmem_agent):
    dmem_agent.mem_dict[0x80000000] = 1

    while True:
        await ClockCycles(dut.clk, 1)
        await ReadWrite()

        dmem_agent.mem_dict[0x80000000] += 1


class SimulationController:
    def __init__(self, dut, instruction_monitor, imem_agent, zmq_addr):
        self.dut = dut
        self.instruction_monitor = instruction_monitor
        self.end_simulation_event = Event()
        self.zmq_context = zmq.Context()
        self.zmq_addr = zmq_addr
        self.imem_agent = imem_agent
        self.incremental_address = 0x1fc00020
        self.pc_unchanged = 0

    async def controller_loop(self):
        global instr_buffer
        with self.zmq_context.socket(zmq.REP) as socket:
            socket.bind(self.zmq_addr)

            await ClockCycles(self.dut.clk, 1)
            await ReadWrite()

            while True:
                stimulus_obj = socket.recv_pyobj()
                self.incremental_address = self.dut.cpu_core_inst.instr_fetch_inst.pc_gen.pc.value + 0x18 - 0xa0000000
                if(stimulus_obj.insn_mem_updates != []):
                    if not isinstance(stimulus_obj, Stimulus):
                        assert False, "Saw bad stimulus message"

                    for data in stimulus_obj.insn_mem_updates:
                        self.prevous_pc=self.dut.cpu_core_inst.instr_fetch_inst.pc_gen.pc
                        self.imem_agent.write_mem(self.incremental_address, data)
                        instr_buffer.append(data)

                        while (len(instr_buffer) > 5):
                            self.prevous_pc=self.dut.cpu_core_inst.instr_fetch_inst.pc_gen.pc
                            buffer_first = instr_buffer[0]
                            i = 0
                            while(buffer_first != self.instruction_monitor.insn.value or not self.instruction_monitor.insn_valid.value):
                                await ClockCycles(self.dut.clk, 1)
                                await ReadWrite()
                                i+=1
                                if(i > 10):
                                    # print("STUCK AT BUFFER")
                                    instr_buffer = instr_buffer[1:]
                                    await do_reset(self.dut)
                                    break
                            self.instruction_monitor.sample_insn_coverage()
                            if(self.prevous_pc != self.dut.cpu_core_inst.instr_fetch_inst.pc_gen.pc):
                                if len(instr_buffer) > 2:
                                    instr_buffer = instr_buffer[1:]
                                else:
                                    instr_buffer = []
                            else:
                                self.pc_unchanged += 1
                                if(self.pc_unchanged > 10):
                                    # print("STUCK AT PC")
                                    await do_reset(self.dut)
                                    instr_buffer = instr_buffer[1:]
                                    self.pc_unchanged = 0
                                    self.prevous_pc = -1

                mips_state_info = MipsStateInfo(
                    last_pc=self.instruction_monitor.last_pc,
                    last_insn=self.instruction_monitor.last_insn,
                )

                socket.send_pyobj(
                    (mips_state_info, self.instruction_monitor.coverage_db)
                )

                if stimulus_obj.finish:
                    self.end_simulation_event.set()
                    break

    def close(self):
        self.zmq_context.term()


@cocotb.test()
async def basic_test(dut):
    from global_shared_types import GlobalCoverageDatabase

    # server_port = "5555" 
    server_port = input("Please enter server's port (e.g. 5050, 5555): ")

    while True:
        #dbus
        dut.dbus_stall.value = 0
        dut.dbus_trans_out.value = 1 #??
        dut.dbus_rddata.value = 0

        #dbus_uncached
        dut.dbus_uncached_stall.value = 0
        dut.dbus_uncached_trans_out.value = 1 #??
        dut.dbus_uncached_rddata.value = 0

        #ibus
        dut.ibus_stall.value = 0
        dut.ibus_ready.value = 1

        dut.intr.value = 0

        imem_agent = MemAgent(dut, "ibus", handle_writes=False)
        dmem_agent = MemAgent(dut, "dbus", handle_writes=True)
        ins_mon = InstructionMonitor(dut)
        imem_agent.load_bin("test_prog.bin", 0xbfc00000)

        cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
        # await debug(dut)
        await do_reset(dut)
        cocotb.start_soon(imem_agent.run_mem())
        cocotb.start_soon(dmem_agent.run_mem())
        cocotb.start_soon(update_magic_loc(dut, dmem_agent))

        await ClockCycles(dut.clk, 1)

        sim_ctrl = SimulationController(
            dut, ins_mon, imem_agent, f"tcp://*:{server_port}"
        )
        with closing(sim_ctrl) as simulation_controller:
            cocotb.start_soon(simulation_controller.controller_loop())

            await simulation_controller.end_simulation_event.wait()
            await ClockCycles(dut.clk, 1)
        break
