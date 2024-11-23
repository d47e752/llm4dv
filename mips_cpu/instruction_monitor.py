import os
import sys

directory = os.path.dirname(os.path.abspath("__file__"))
sys.path.insert(0, os.path.dirname(directory))

from ibex_cpu.shared_types import CoverageDatabase
from mips_cpu.instructions import Instr, Encoding


class InstructionMonitor:
    def __init__(self, dut):
        self.clk = dut.clk
        self.insn_valid = dut.cpu_core_inst.instr_fetch_inst.pc_gen.pc_en
        self.insn_pc = dut.cpu_core_inst.instr_fetch_inst.pc_gen.pc
        self.insn = dut.cpu_core_inst.instr_fetch_inst.decoder_inst1.instr
        self.coverage_db = CoverageDatabase(instructions={}, cross_coverage={})
        self.last_pc = None
        self.last_insn = None

        for instr in Instr:
            self.coverage_db.instructions[instr] = {
                cov: 0 for cov in instr.type().coverpoints()
            }
            self.coverage_db.cross_coverage[instr] = {
                (other_instr, cov): 0
                for (other_instr, cov) in instr.type().cross_coverpoints()
            }

    def sample_insn_coverage(self):
        if self.insn_valid.value == 0:
            self.last_pc = None
            self.last_insn = None
            return

        insn = Encoding(self.insn.value, self.insn_pc.value).typed()
        # op = "{0:06b}".format((self.insn.value & 0xFC000000) >> 26)
        # funct = "{0:06b}".format((self.insn.value & 0x3F))

        if insn is not None:
            try:
                mnemonic = insn.instruction()
            except AssertionError:  # Valid MIPS instruction, but not in instruction.py
                print(
                    f">>>>> Valid MIPS instruction {hex(insn.encoding)}, but not in instruction.py \n"
                )
                return

            for coverpoint in insn.sample_coverage():
                self.coverage_db.instructions[mnemonic][coverpoint] += 1

            if (
                self.last_insn is not None
                and (last_insn := Encoding(self.last_insn, self.last_pc).typed()) is not None
            ):
                for insn_cov in insn.sample_cross_coverage(last_insn):
                    self.coverage_db.cross_coverage[mnemonic][insn_cov] += 1
        # else:
        #     print("Instruction is None!")

        self.last_pc = int(self.insn_pc.value)
        self.last_insn = int(self.insn.value)
