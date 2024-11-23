#!/bin/env python3
# Copyright ***
# Copyright ***** contributors.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

import csv
import os
import sys
from datetime import datetime
import argparse

import zmq
import pickle
from contextlib import closing
from pathlib import Path

from models.llm_azure import AzureOpenai

directory = os.path.dirname(os.path.abspath("__file__"))
sys.path.insert(0, os.path.dirname(directory))

from agents.agent_LLM import *
from agents.agent_IC_dumb import *
from agents.agent_random import *
from loggers.logger_csv import CSVLogger
from loggers.logger_txt import TXTLogger
from models.llm_gpt import ChatGPT
from models.llm_openrouter import OpenRouter
from ibex_cpu.shared_types import *
from stimuli_extractor import *
from stimuli_filter import *
from prompt_generators.prompt_generator_template_IC import *

increment_address = True


class StimulusSender:
    def __init__(self, zmq_addr):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(zmq_addr)

    def send_stimulus(self, stimulus_obj):
        self.socket.send_pyobj(stimulus_obj)
        state_coverage_obj = self.socket.recv_pyobj()

        if not isinstance(state_coverage_obj, tuple):
            raise RuntimeError("Bad format of coverage response")
        if not isinstance(state_coverage_obj[0], IbexStateInfo):
            raise RuntimeError("Bad format of coverage response element 0")
        if not isinstance(state_coverage_obj[1], CoverageDatabase):
            raise RuntimeError("Bad format of coverage response element 1")

        return state_coverage_obj

    def close(self):
        if self.socket:
            self.socket.close()


def random_experiment():
    print("Running random experiment on IC...")

    server_ip_port = input(
        "Please enter server's IP and port (e.g. 127.0.0.1:5050, 128.232.65.218:5555): "
    )

    # server_ip_port = "0.0.0.0:5050"

    CYCLES = 1000000

    agent = RandomAgent4IC(total_cycle=CYCLES, seed=datetime.now().timestamp())

    stimulus = Stimulus(insn_mem_updates=[], finish=False)
    g_dut_state = GlobalDUTState()
    g_coverage = GlobalCoverageDatabase()

    with closing(StimulusSender(f"tcp://{server_ip_port}")) as stimulus_sender:
        while not agent.end_simulation(g_dut_state, g_coverage):
            stimulus.insn_mem_updates = agent.generate_next_value(
                g_dut_state, g_coverage
            )
            # print(
            #     f"Generated updates[:4]: "
            #     f"{list(map(lambda p: (hex(p[0]), hex(p[1])), stimulus.insn_mem_updates))[:4]}\n"
            # )
            ibex_state, coverage = stimulus_sender.send_stimulus(stimulus)
            g_dut_state.set(ibex_state)
            g_coverage.set(coverage)

            if ibex_state.last_pc is not None:
                print(
                    f"DUT state: {ibex_state.last_pc:08x} {ibex_state.last_insn:08x}\n"
                )

        stimulus.finish = True
        _, final_coverage = stimulus_sender.send_stimulus(stimulus)
        final_coverage.output()

        g_coverage.set(final_coverage)
        print(f"Final coverage rate: {g_coverage.get_coverage_rate()}")


def main(model_name="meta-llama/llama-2-70b-chat", missed_bin_sampling="RANDOM", best_iter_message_sampling="Recent Responses", dialogue_restarting="rst_plan_Low_Tolerance", buffer_resetting="STABLE", code_summary_type=0, few_shot=0):
    if(dialogue_restarting == "rst_plan_Normal_Tolerance"):
        dialogue_restarting = rst_plan_Normal_Tolerance
    elif (dialogue_restarting == "rst_plan_Low_Tolerance"):
        dialogue_restarting = rst_plan_Low_Tolerance
    elif(dialogue_restarting == "rst_plan_High_Tolerance"):
        dialogue_restarting = rst_plan_High_Tolerance
    elif (dialogue_restarting == "rst_plan_Coverage_RateBased_Tolerance"):
        dialogue_restarting = rst_plan_Coverage_RateBased_Tolerance
    print("Running main experiment on IC...\n")

    # server_ip_port = "0.0.0.0:5555"
    server_ip_port = input(
        "Please enter server's IP and port (e.g. 127.0.0.1:5050, 128.232.65.218:5555): "
    )

    prefix = f"./logs/"
    t = datetime.now()
    t = t.strftime("%Y%m%d_%H%M%S")

    # build components
    prompt_generator = TemplatePromptGenerator4IC2(
        bin_descr_path="../examples_IC/bins_description.txt",
        sampling_missed_bins_method=missed_bin_sampling,
        code_summary_type=int(code_summary_type),
        easy_cutoff = 50,
        few_shot=int(few_shot)
    )

    stimulus_generator = AzureOpenai(
        system_prompt=prompt_generator.generate_system_prompt(),
        best_iter_buffer_resetting=buffer_resetting,
        compress_msg_algo=best_iter_message_sampling.replace("_", " "),
        prioritise_harder_bins=False,
        model_name=model_name
    )
    if(increment_address):
        extractor = UniversalExtractor(1)
        stimulus_filter = UniversalFilter([[0x0, 0xFFFFFFFF]], True)
    else:
        extractor = ICExtractor()
        stimulus_filter = ICFilter(0x0, 0xFFFFFFFF)

    # build loggers
    prefix = "./logs/" + model_name + "_"
    if(increment_address):
        prefix = prefix.replace(prefix.split("/")[-2], prefix.split("/")[-2] + "/incremental")
    else:
        prefix = prefix.replace(prefix.split("/")[-2], prefix.split("/")[-2] + "/memory_update")

    if("gpt-3" in model_name):
        prefix = prefix.replace("openai", "openai_gpt-3")
    elif("gpt-4" in model_name):
        prefix = prefix.replace("openai", "openai_gpt-4")

    if("llama-2-70b-chat" in model_name):
        prefix = prefix.replace("meta-llama", "meta-llama-2")
    elif("codellama-70b-instruct" in model_name):
        prefix = prefix.replace("meta-llama", "meta-llama-code")
    elif("llama-3-70b" in model_name):
        prefix = prefix.replace("meta-llama", "meta-llama-3")

    if(missed_bin_sampling == "RANDOM"):
        prefix += "1_"
    elif(missed_bin_sampling == "NEWEST"):
        prefix += "2_"
    elif(missed_bin_sampling == "MIXED"):
        prefix += "3_"

    if(best_iter_message_sampling == "Recent_Responses"):
        prefix += "I_"
    elif(best_iter_message_sampling == "Successful_Responses"):
        prefix += "II_"
    elif(best_iter_message_sampling == "Mixed_Recent_and_Successful_Responses"):
        prefix += "III_"
    elif(best_iter_message_sampling == "Successful_Difficult_Responses"):
        prefix += "IV_"

    if(dialogue_restarting == rst_plan_Normal_Tolerance):
        prefix += "a_"
    elif(dialogue_restarting == rst_plan_Low_Tolerance):
        prefix += "b_"
    elif(dialogue_restarting == rst_plan_High_Tolerance):
        prefix += "c_"
    elif(dialogue_restarting == rst_plan_Coverage_RateBased_Tolerance):
        prefix += "d_"

    if(buffer_resetting == "CLEAR"):
        prefix += "i"
    elif(buffer_resetting == "KEEP"):
        prefix += "ii"
    elif(buffer_resetting == "STABLE"):
        prefix += "iii"

    if(code_summary_type == "1"):
        prefix += "_with_code"

    if(few_shot == "1"):
        prefix += "_few_shot"
    
    prefix += "/"

    Path(prefix).mkdir(parents=True, exist_ok=True)

    t = datetime.now()
    t = t.strftime("%Y%m%d_%H%M%S")
    logger_txt = TXTLogger(f"{prefix}{t}.txt")
    logger_csv = CSVLogger(f"{prefix}{t}.csv")


    # create agent
    agent = LLMAgent(
        prompt_generator,
        stimulus_generator,
        extractor,
        stimulus_filter,
        [logger_txt, logger_csv],
        dialog_bound=700,
        rst_plan=dialogue_restarting,
        bin_count=196
    )
    print("Agent successfully built\n")

    # agent = DumbAgent4IC()

    stimulus = Stimulus(insn_mem_updates=[], finish=False)
    g_dut_state = GlobalDUTState()
    g_coverage = GlobalCoverageDatabase()

    with closing(StimulusSender(f"tcp://{server_ip_port}")) as stimulus_sender:
        while not agent.end_simulation(g_dut_state, g_coverage):
            stimulus.insn_mem_updates = agent.generate_next_value(
                g_dut_state, g_coverage, is_ic=True
            )
            # print(
            #     f"Generated updates[:10]: "
            #     f"{list(map(lambda p: (hex(p[0]), hex(p[1])),stimulus.insn_mem_updates))[:10]}\n"
            # )
            ibex_state, coverage = stimulus_sender.send_stimulus(stimulus)
            g_dut_state.set(ibex_state)
            g_coverage.set(coverage)

            if ibex_state.last_pc is not None:
                print(
                    f"DUT state: {ibex_state.last_pc:08x} {ibex_state.last_insn:08x}\n"
                )

        stimulus.finish = True
        _, final_coverage = stimulus_sender.send_stimulus(stimulus)
        final_coverage.output()

        g_coverage.set(final_coverage)
        print(f"Final coverage rate: {g_coverage.get_coverage_rate()}")


def budget_experiment():
    print("Running budget experiment on IC...")

    INIT_BUDGET = 10000000
    print(f"Start with BUDGET={INIT_BUDGET}\n")

    BUDGET = Budget(budget_per_trial=INIT_BUDGET, total_budget=INIT_BUDGET)

    server_ip_port = input(
        "Please enter server's IP and port (e.g. 127.0.0.1:5050, 128.232.65.218:5555): "
    )

    t = datetime.now()
    t = t.strftime("%Y%m%d_%H%M%S")
    prefix = f"./logs/{t}_budget/"
    if not os.path.exists(prefix):
        os.makedirs(prefix)

    header = ["Trial #", "Message cnt", "Token cnt", "Coverage rate", "Coverage plan"]
    data = []
    trial_cnt = 0

    with open(f"{prefix}{t}_summary.csv", "a+", encoding="UTF8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

    while BUDGET.total_budget > 0:
        trial_cnt += 1
        BUDGET.init_budget = min(BUDGET.init_budget, BUDGET.total_budget)
        BUDGET.budget = BUDGET.init_budget

        # build components
        prompt_generator = TemplatePromptGenerator4IC2(
            bin_descr_path="../examples_IC/bins_description.txt",
            sampling_missed_bins_method="ICNEWEST",
        )

        stimulus_generator = ChatGPT(
            max_gen_tokens=1000,
            system_prompt=prompt_generator.generate_system_prompt(),
            best_iter_buffer_resetting="STABLE",
            compress_msg_algo="best 3",
            prioritise_harder_bins=False,
        )
        extractor = ICExtractor()
        stimulus_filter = ICFilter(0x0, 0xFFFFFFFF)

        # build loggers
        logger_txt = TXTLogger(f"{prefix}{t}_trial_{trial_cnt}.txt")
        logger_csv = CSVLogger(f"{prefix}{t}_trial_{trial_cnt}.csv")

        # create agent
        agent = LLMAgent(
            prompt_generator,
            stimulus_generator,
            extractor,
            stimulus_filter,
            [logger_txt, logger_csv],
            dialog_bound=1000,
            rst_plan=rst_plan_Low_Tolerance,
            token_budget=BUDGET,
        )
        print("Agent successfully built\n")

        stimulus = Stimulus(insn_mem_updates=[], finish=False)
        g_dut_state = GlobalDUTState()
        g_coverage = GlobalCoverageDatabase()

        with closing(StimulusSender(f"tcp://{server_ip_port}")) as stimulus_sender:
            while not agent.end_simulation(g_dut_state, g_coverage):
                stimulus.insn_mem_updates = agent.generate_next_value(
                    g_dut_state, g_coverage, is_ic=True
                )
                print(
                    f"Generated updates[:4]: "
                    f"{list(map(lambda p: (hex(p[0]), hex(p[1])), stimulus.insn_mem_updates))[:4]}\n"
                )
                ibex_state, coverage = stimulus_sender.send_stimulus(stimulus)
                g_dut_state.set(ibex_state)
                g_coverage.set(coverage)

                if ibex_state.last_pc is not None:
                    print(
                        f"DUT state: {ibex_state.last_pc:08x} {ibex_state.last_insn:08x}\n"
                    )

            stimulus.finish = True
            _, final_coverage = stimulus_sender.send_stimulus(stimulus)
            # final_coverage.output()
            g_coverage.set(final_coverage)

            data.append(
                [
                    trial_cnt,
                    agent.total_msg_cnt,
                    BUDGET.init_budget - BUDGET.budget,
                    g_coverage.get_coverage_rate()[0],
                    str(
                        dict(
                            filter(
                                lambda p: p[1] != 0,
                                g_coverage.get_coverage_plan().items(),
                            )
                        )
                    ),
                ]
            )
            with open(
                f"{prefix}{t}_summary.csv", "a+", encoding="UTF8", newline=""
            ) as f:
                writer = csv.writer(f)
                writer.writerow(data[-1])

            BUDGET.total_budget -= BUDGET.init_budget - BUDGET.budget
            print(
                f">>>> Finished trial #{trial_cnt} at dialog #{agent.dialog_index}, message #{agent.msg_index}, \n"
                f"with total {agent.total_msg_cnt} messages \n"
                f"and total {BUDGET.init_budget - BUDGET.budget} tokens \n"
                f"Coverage rate: {g_coverage.get_coverage_rate()}\n"
                f"BUDGET left: {BUDGET.total_budget} tokens\n"
            )

    print("\n******** FINAL RESULT ********\n")
    for entry in data:
        print(
            f"Trial #{entry[0]}, Msg cnt: {entry[1]}, Token cnt: {entry[2]}, Coverage: {entry[3]}"
        )
    min_hit_id = np.argmin([entry[3] for entry in data])
    max_hit_id = np.argmax([entry[3] for entry in data])
    print(
        f"\n"
        f"Total trial cnt: {trial_cnt}\n"
        f"Total token cnt: {INIT_BUDGET - BUDGET.total_budget}\n"
        f"Min coverage: {data[min_hit_id][3]} by trial #{data[min_hit_id][0]}\n"
        f"Max coverage: {data[max_hit_id][3]} by trial #{data[max_hit_id][0]}\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--model_name", type=str, default="meta-llama/llama-2-70b-chat")
    parser.add_argument("--missed_bin_sampling", type=str, default="RANDOM")
    parser.add_argument("--best_iter_message_sampling", type=str, default="Recent_Responses")
    parser.add_argument("--dialogue_restarting", type=str, default="rst_plan_Low_Tolerance")
    parser.add_argument("--buffer_resetting", type=str, default="STABLE")
    parser.add_argument("--code_summary_type", type=int, default=0)
    parser.add_argument("--few_shot", type=int, default=0)
    args = parser.parse_args()
    main(args.model_name, args.missed_bin_sampling, args.best_iter_message_sampling, args.dialogue_restarting, args.buffer_resetting, args.code_summary_type, args.few_shot)
    # Example: python generate_stimulus.py --model_name meta-llama/llama-2-70b-chat --missed_bin_sampling MIXED --best_iter_message_sampling Successful_Responses --dialogue_restarting rst_plan_Low_Tolerance --buffer_resetting KEEP --code_summary_type 0 --few_shot 0


    # If you want to run CRT
    # random_experiment()