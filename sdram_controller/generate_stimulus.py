#!/bin/env python3
import csv
import time
from datetime import datetime
import zmq
import pickle
from contextlib import closing
import sys
import os
import numpy as np
from pathlib import Path
import argparse

from models.llm_azure import AzureOpenai

directory = os.path.dirname(os.path.abspath("__file__"))
sys.path.insert(0, os.path.dirname(directory))
# print(sys.path)

from sdram_controller.shared_types import *
from global_shared_types import *
from agents.agent_random import *
from agents.agent_LLM import *
from prompt_generators.prompt_generator_template_SDRAM import *
from models.llm_gpt import ChatGPT
from models.llm_openrouter import OpenRouter
from loggers.logger_csv import CSVLogger
from loggers.logger_txt import TXTLogger

class StimulusSender:
    def __init__(self, zmq_addr):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(zmq_addr)

    def send_stimulus(self, stimulus_obj):
        self.socket.send_pyobj(stimulus_obj)
        state_coverage_obj = self.socket.recv_pyobj()

        if not isinstance(state_coverage_obj, tuple):
            print(state_coverage_obj)
            raise RuntimeError("Bad format of coverage response")
        if not isinstance(state_coverage_obj[0], DUTState):
            print(state_coverage_obj[0])
            raise RuntimeError("Bad format of coverage response element 0")
        if not isinstance(state_coverage_obj[1], CoverageDatabase):
            print(state_coverage_obj[1])
            raise RuntimeError("Bad format of coverage response element 1")

        return state_coverage_obj

    def close(self):
        if self.socket:
            self.socket.close()

def random_experiment():
    print("Running random experiment on SDRAM...\n")

    server_ip_port = input(
        "Please enter server's IP and port (e.g. 127.0.0.1:5050, 128.232.65.218:5555): "
    )
    # server_ip_port = "0.0.0.0:5050"

    CYCLES = 1000000
    agent = RandomAgent4SDRAM(total_cycle=CYCLES, seed=int(datetime.now().timestamp()))

    # run test
    stimulus = Stimulus(value=0, finish=False)
    g_dut_state = GlobalDUTState()
    g_coverage = GlobalCoverageDatabase()

    with closing(StimulusSender(f"tcp://{server_ip_port}")) as stimulus_sender:
        while not agent.end_simulation(g_dut_state, g_coverage):
            stimulus.value = agent.generate_next_value(g_dut_state, g_coverage)
            if(isinstance(stimulus.value, int)):
                stimulus.value = [0,0,0]
            dut_state, coverage = stimulus_sender.send_stimulus(stimulus)
            g_dut_state.set(dut_state)
            g_coverage.set(coverage)
            print(
                f"Coverage rate: {g_coverage.get_coverage_rate()}\n"
            )

        coverage_plan = {
            k: v for (k, v) in g_coverage.get_coverage_plan().items() if v > 0
        }
        print(
            f"Finished random agent on AGILE weight bank with {CYCLES} cycles \n"
            f"Hits: {coverage_plan}, \n"
            f"Coverage rate: {g_coverage.get_coverage_rate()}\n"
        )

        stimulus.value = None
        stimulus.finish = True
        stimulus_sender.send_stimulus(stimulus)

def main(model_name="meta-llama/llama-2-70b-chat", missed_bin_sampling="RANDOM", best_iter_message_sampling="Recent Responses", dialogue_restarting="rst_plan_Low_Tolerance", buffer_resetting="STABLE", code_summary_type = 0, few_shot = 0):
    if(dialogue_restarting == "rst_plan_Normal_Tolerance"):
        dialogue_restarting = rst_plan_Normal_Tolerance
    elif (dialogue_restarting == "rst_plan_Low_Tolerance"):
        dialogue_restarting = rst_plan_Low_Tolerance
    elif(dialogue_restarting == "rst_plan_High_Tolerance"):
        dialogue_restarting = rst_plan_High_Tolerance
    elif (dialogue_restarting == "rst_plan_Coverage_RateBased_Tolerance"):
        dialogue_restarting = rst_plan_Coverage_RateBased_Tolerance
    print("Running main experiment on SDRAM...")

    # server_ip_port = "0.0.0.0:5555"
    server_ip_port = input(
        "Please enter server's IP and port (e.g. 127.0.0.1:5050, 128.232.65.218:5555): "
    )

    # build components
    prompt_generator = TemplatePromptGeneratorSDRAM(
        bin_descr_path="../examples_SDRAM/bins_description.txt",
        dut_code_path="src/sdram_controller.sv",
        tb_code_path="sdram_controller_cocotb.py",
        sampling_missed_bins_method=missed_bin_sampling,
        code_summary_type=int(code_summary_type)
    )
    
    stimulus_generator = AzureOpenai(
        system_prompt=prompt_generator.generate_system_prompt(),
        best_iter_buffer_resetting=buffer_resetting,
        compress_msg_algo=best_iter_message_sampling.replace("_", " "),
        prioritise_harder_bins=False,
        model_name=model_name
    )

    extractor = UniversalExtractor(3)
    stimulus_filter = UniversalFilter([[0,1],[0,1],[0,1]])

    # build loggers
    prefix = "./logs/" + model_name + "_"

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
        dialog_bound=300,
        rst_plan=dialogue_restarting,
        bin_count=7
    )
    print("Agent successfully built\n")

    # agent = RandomAgent(3000000)

    # run test
    g_dut_state = GlobalDUTState()
    g_coverage = GlobalCoverageDatabase()
    stimulus = Stimulus(value=0, finish=False)

    with closing(StimulusSender(f"tcp://{server_ip_port}")) as stimulus_sender:
        while not agent.end_simulation(g_dut_state, g_coverage):
            stimulus.value = agent.generate_next_value(g_dut_state, g_coverage)
            if(isinstance(stimulus.value, int)):
                stimulus.value = [0,0,0]
            print(stimulus)
            dut_state, coverage = stimulus_sender.send_stimulus(stimulus)
            g_dut_state.set(dut_state)
            g_coverage.set(coverage)

        dut_state, coverage = stimulus_sender.send_stimulus(Stimulus(value=[0,0,0], finish=True))

        g_coverage.set(coverage)
        coverage_plan = {
            k: v for (k, v) in g_coverage.get_coverage_plan().items() if v > 0
        }
        print(
            f"Finished with hits: {coverage_plan}\n"
            f"Coverage: {g_coverage.get_coverage_rate()}\n"
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