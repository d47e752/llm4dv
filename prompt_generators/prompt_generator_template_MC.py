# Copyright ***
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

from prompt_generators.prompt_generator_template import *
from mips_cpu.instructions import Instr, Cov


class TemplatePromptGenerator4MC(TemplatePromptGenerator):
    IMEM_LB = "0x1fc00028"
    IMEM_UB = "0x1fc00400"

    def __init__(
        self,
        dut_code_path: str = "../examples_MC/dut_code.txt",
        tb_code_path: str = "../examples_MC/tb_code.txt",
        bin_descr_path: str = "../examples_MC/bins_description.txt",
        code_summary_type: int = 0,  # 0: no code, 1: code, 2: summary
        sampling_missed_bins_method: Union[str, None] = None,
        easy_cutoff: int = 100,
        few_shot: int = 0
    ):
        super().__init__(
            dut_code_path,
            tb_code_path,
            bin_descr_path,
            code_summary_type,
            sampling_missed_bins_method,
            easy_cutoff,
            few_shot
        )

    def generate_system_prompt(self) -> str:
        # TODO: refine SYSTEM prompt & output format (output updates OR whole instr memo?)
        return (
            f"Please output a list of hexadecimal integers only, "
            f"each integer between 0x0 and 0xffffffff. \n"
            f"Do not give any explanations. \n"
            f"Output format: [a, b, c ...]."
        )

    def _load_introduction(self) -> str:
        if self.code_summary_type == 1:
            raise NotImplementedError
        elif self.code_summary_type == 0:
            return (
                "You will receive a description of bins (i.e. test cases) of a testbench for "
                "a hardware device under test (DUT), which is a MIPS CPU. "
                "Then, you are going to generate a list of 32-bit integers between "
                "0x0 and 0xffffffff to update the instruction memory in order to cover these test cases, "
                "where the integer represents a MIPS instruction, next loaded into instruction memory. DO NOT SUPPLY 0x0 AS AN INSTRUCTION\n"
            )
        else:
            raise NotImplementedError

    def _load_code_summary(self, dut_code_path, tb_code_path) -> str:
        if self.code_summary_type == 0:
            return ""
        elif self.code_summary_type == 1:
            raise NotImplementedError
        else:
            raise NotImplementedError

    def _load_bins_summary(self, bin_descr_dir, **kwargs) -> str:
        with open(bin_descr_dir, "r") as f:
            bins_description = f.read()
        tb_summary = (
            f"We are working with a CPU capable of executing MIPS instructions. "
            f"Remember that one instruction is 32 bits (8 bytes).\n"
            f"Our objective is to update the CPU's instruction memory with a sequence "
            f"of 32-bit addresses and corresponding 32-bit instructions. The goal is "
            f"to ensure that, when the CPU resumes executing instructions from the "
            f"current PC, it covers the bins (i.e. test cases) that are of interest to us. \n"
            f"Here's the description of the bins that are of interest to us:\n"
            f"------\n"
            f"BINS DESCRIPTION\n"
            f"{bins_description}\n"
            f"------\n"
        )
        tb_summary += self._load_examples()
        return tb_summary

    def _load_examples(self) -> str:
        if(self.few_shot == 1):
            examples = (
                f"Here are a few examples:\n"
                f"- 0x0067a020 => op=000000 rs=00011 rt=00111 rd=10100 sa=00000 funct=100000 => add_seen covered\n"
                f"- 0x0c00000a => op=000011 instr_index=00000000000000000000001010 => jal_seen covered\n"
                f"- 0x00001403 => op=000000 rs=00000 rt=00000 rd=00101 sa=00011 funct=000000 => sll_seen, sll_zero_src covered\n"
                f"- 0x00f7a2a3 => op=101011 rs=01111 rt=01111 imm=0000000000000101 => sw_seen, sw_same_src covered\n"
                f"- 0xa4010000 => op=101001 rs=00000 rt=00001 imm=0000000000000000 => sh_seen, sh_zero_src covered\n"
                f"- 0x0022182b, 0x00652026 => op=000000 rs=00001 rt=00010 rd=00011 sa=00000 funct=101011, op=000000 rs=00011 rt=00101 rd=00100 sa=00000 funct=100110 => sltu_seen, xor_seen, sltu->xor_raw_hazard covered\n"
                f"------\n"  
            )
        else:
            examples = ""
        return examples

    def _load_init_question(self) -> str:
        init_question = (
            f"Following the bins description, generate a list, which can be empty if "
            f"necessary, of instructions in 32-bit hexadecimal format "
            f"to update the CPU's memory, ensuring it covers the specified bins upon resuming "
            f"execution from the current PC. Make sure the instructions are valid MIPS instruction codes."
            f"Remember that one instruction is 32 bits (8 bytes).\n"
        )
        return init_question

    def _load_result_summary(self, **kwargs) -> str:
        if kwargs["response_invalid"]:
            result_summary = (
                "Your response doesn't answer my query. \n"
                "Please generate a list of address-instruction pairs in 32-bit hexadecimal "
                "format (i.e. hex integers between 0x0 and 0xffffffff), with output format: "
                "[a, b, c, ...].\n"
            )
        elif kwargs["update_invalid"]:
            result_summary = (
                "Your list of updates was invalid, either because the instructions you provided are not valid R-type, S-type, or J-type MIPS "
                "instructions. Try to amend it in your new response. \n"
                f"The CPU has executed numerous instructions following your last update. The last "
                f"instruction performed was {kwargs['last_instr']}. \n"
            )
        else:
            result_summary = (
                f"Thanks for your response.\n"
                f"The CPU has successfully executed numerous instructions following your update. "
                f"The last instruction performed was {kwargs['last_instr']}. \n"
            )

        # TODO: pass in current instr memo??
        result_summary += (
            f"You will now observe the bins haven't been achieved by the CPU, and proceed to "
            f"generate another list, which can be empty if necessary, "
            f"of instructions to further modify the CPU's memory, ensuring it "
            f"covers the previously unreached bins (i.e. test cases) upon resuming execution "
            f"from the current PC.\n"
            f"Here are {'some of ' if self.sampling_missed_bins else ''}the unreached bins:\n"
        )
        return result_summary

    def _load_coverage_difference_prompts_dict(self) -> Dict[str, str]:
        basic_bins = {
            "seen": [],
            "zero_dst": [],
            "zero_src": [],
            "same_src": [],
            "br_backwards": [],
            "br_forwards": [],
        }
        for instr in Instr:
            for cov in instr.type().coverpoints():
                basic_bins[cov.value].append(instr.value)

        raw_bins = []
        for instr in Instr:
            for prev_instr, cov in instr.type().cross_coverpoints():
                raw_bins.append((prev_instr.value, instr.value, cov.value))

        basic_bins_difference = {}
        for op in basic_bins["seen"]:
            basic_bins_difference[
                f"{op}_seen"
            ] = f"- {op}_seen: the CPU hasn't performed the operation {op}.\n"
        for op in basic_bins["zero_dst"]:
            basic_bins_difference[f"{op}_zero_dst"] = (
                f"- {op}_zero_dst: the CPU hasn't executed an instruction "
                f"that performs the operation {op} with register zero as "
                f"the destination register.\n"
            )
        for op in basic_bins["zero_src"]:
            basic_bins_difference[f"{op}_zero_src"] = (
                f"- {op}_zero_src: the CPU hasn't executed an instruction "
                f"that performs the operation {op} with register zero as "
                f"one of the source registers.\n"
            )
        for op in basic_bins["same_src"]:
            basic_bins_difference[f"{op}_same_src"] = (
                f"- {op}_same_src: the CPU hasn't executed an instruction "
                f"that performs the operation {op} with same source registers.\n"
            )
        for op in basic_bins["br_backwards"]:
            basic_bins_difference[f"{op}_br_backwards"] = (
                f"- {op}_br_backwards: the CPU hasn't performed a {op} "
                f"operation that makes a backward jump.\n"
            )
        for op in basic_bins["br_forwards"]:
            basic_bins_difference[f"{op}_br_forwards"] = (
                f"- {op}_br_backwards: the CPU hasn't performed a {op} "
                f"operation that makes a forward jump.\n"
            )

        raw_bins_difference = {
            f"{prev_instr}->{instr}_{cov}": f"- {prev_instr}->{instr}_{cov}: the CPU hasn't perform a "
            f"{prev_instr} operation followed by a {instr} operation with "
            f"RaW hazard, in which the second operation has a source register "
            f"that is the same as the destination register of the first operation.\n"
            for prev_instr, instr, cov in raw_bins
        }

        coverage_difference_template = {
            **basic_bins_difference,
            **raw_bins_difference,
        }
        return coverage_difference_template

    def _load_iter_question(self, **kwargs) -> str:
        if kwargs["response_invalid"]:
            iter_question = (
                f"Please generate a list, which can be empty if necessary, of "
                f"instructions in 32-bit hexadecimal format (i.e. "
                f"hex integers between 0x0 and 0xffffffff), with output format: "
                f"[a, b, c, ...]. Make sure the instructions "
                f"are valid MIPS instruction codes."
                f"Remember that one instruction is 32 bits (8 bytes).\n"
            )
        else:
            iter_question = (
                f"Please generate a list, which can be empty if necessary, of instructions "
                f"in 32-bit hexadecimal format to further update the CPU's memory, "
                f"ensuring it covers the specified unreached bins (i.e. test cases) upon resuming "
                f"execution from the current PC. Make sure the instructions are valid R-type, S-type, "
                f"or J-type instructions. We encourage you to use a diverse variety of operations. "
                f"Remember that one instruction is 32 bits (8 bytes).\n"
            )
        return iter_question


# # Succinct task introduction
# class TemplatePromptGenerator4IC2(TemplatePromptGenerator4IC1):
#     def __init__(
#         self,
#         dut_code_path: str = "../examples_IC/dut_code.txt",
#         tb_code_path: str = "../examples_IC/tb_code.txt",
#         bin_descr_path: str = "../examples_IC/bins_description.txt",
#         code_summary_type: int = 0,  # 0: no code, 1: code, 2: summary
#         sampling_missed_bins_method: Union[str, None] = None,
#     ):
#         super().__init__(
#             dut_code_path,
#             tb_code_path,
#             bin_descr_path,
#             code_summary_type,
#             sampling_missed_bins_method,
#         )

#     def generate_initial_prompt(self, **kwargs) -> str:
#         with open(self.bin_descr_path, "r") as f:
#             bins_description = f.read()
#         prompt = (
#             # TODO: pass in current instr memo??
#             f"We are working with a CPU capable of executing MIPS instructions. "
#             f"The CPU's instruction memory is defined within the address range of "
#             f"{self.IMEM_LB} to {self.IMEM_UB}."
#             f"The program counter (PC) is currently set to "
#             f"{kwargs['current_pc']}. \n"
#             f"Our objective is to update the CPU's instruction memory with a sequence "
#             f"of 32-bit addresses and corresponding 32-bit instructions. The goal is "
#             f"to ensure that, when the CPU resumes executing instructions from the "
#             f"current PC, it covers the bins (i.e. test cases) that are of interest to us. \n"
#             f"Here's the description of the bins that are of interest to us:\n"
#             "------\n"
#             "BINS DESCRIPTION\n"
#             f"{bins_description}"
#             "------\n"
#             f"Following the bins description, generate a list, which can be empty if "
#             f"necessary, of address-instruction pairs $(a, i)$ in 32-bit hexadecimal format "
#             f"to update the CPU's memory, ensuring it covers the specified bins upon resuming "
#             f"execution from the current PC. Make sure the addresses $a$ are in the range of "
#             f"{self.IMEM_LB} to {self.IMEM_UB}, and the instructions $i$ are VALID R-type, S-type, "
#             f"or J-type instructions. We encourage you to make updates near the current PC ({kwargs['current_pc']}), "
#             f"and update addresses into diverse variety of operations. \n"
#         )
#         return prompt
