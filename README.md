
<!--Copyright ***

Copyright ***** contributors.

Licensed under the Apache License, Version 2.0, see LICENSE for details.

SPDX-License-Identifier: Apache-2.0

-->

# LLM for Design Verification

  

___LLM4DV___ is a benchmarking framework utilising large language models in hardware design verification.

This project provides a framework for incorporating LLMs in test stimuli generation (i.e.

generating inputs for testing a device). The goal is to generate stimuli to cover most of the test bins

(i.e. test cases) from a predefined coverage plan with the LLM using as few tokens as possible.

  

This repository contains a number of designs along with cocotb testbenches to enable research into

exploring ML techniques for DV. The eight designs are:

  

- stride_detector - A mock design of the core of a prefetcher

- ibex_decoder - A standalone instantiaton of the decoder from the Ibex RISC-V

core

- ibex_cpu - The full Ibex RISC-V core

- agile_prefetcher/weight_bank - The weight bank of AGILE (has since been renamed [AMPLE](https://github.com/pgimenes/ample))

- agile_prefetcher/fetch_tag - The fetch tag of AGILE (has since been renamed [AMPLE](https://github.com/pgimenes/ample))

- async_fifo - An [Asynchronous FIFO](https://github.com/dpretet/async_fifo)

- sdram_controller - A simple [SDRAM Controller](https://github.com/stffrdhrn/sdram-controller)

- mips_cpu - A MIPS_CPU core ([nontrivial-mips](https://github.com/trivialmips/nontrivial-mips))

  

## Getting started

  

The simulation runs as a client-server model. The client side generates stimuli to the server. The server

side receives stimuli, computes coverage, and returns the DUT state and coverage back to the client.

  

### Software pre-requisites

  

You will need to install __cocotb__, you can find the installation guide here:

https://docs.cocotb.org/en/stable/install.html

  

Additionally, you'll need the dependencies listed in `python-requirements.txt`

which can be installed with pip:

  

> pip install --user -r python-requirements.txt

  

(These requirements are needed for both the client and server)

  

__Verilator__ is used as the simulator. Pre-built binary packages are often out of

date and a recent (v5 onwards) version of verilator is required, so it is

recommended you build the latest stable tag (v5.012 at time of writing) from

source as described here:

https://verilator.org/guide/latest/install.html#detailed-build-instructions

  

You may also want __GTKWave__: https://gtkwave.sourceforge.net/, this allows you to

view the waveform output from a simulator run. Again it is recommended you build

this from source. Note this is strictly optional and you may not have any need

for it at all.

  

### Running the simulation

  

1. Run `make` for the server and `generate_stimulus.py` for the client in the module's directory.

+ You may need to run `make` under a Python venv.

2. Specify port / IP address & port when the server and client processes start.

3. Running logs will be stored as txt and csv files in `./[module]/logs` as default.

  

You can specify strategies for stimulus generation on the client side. The `generate_stimulus.py` takes in the following arguments:
| Argument | Options |
|--|--|
| model_name | Any model supported by [OpenRouter](https://openrouter.ai/) (e.g. `meta-llama/llama-2-70b-chat`) |
| missed_bin_sampling | `RANDOM` / `MIXED` / `NEWEST` |
| best_iter_message_sampling | `Recent_Responses` / `Successful_Responses` / `Mixed_Recent_and_Successful_Responses` / `Successful_Difficult_Responses` |
| dialogue_restarting | `rst_plan_Normal_Tolerance` / `rst_plan_Low_Tolerance` / `rst_plan_High_Tolerance` / `rst_plan_Coverage_RateBased_Tolerance` |
| buffer_resetting | `CLEAR` / `KEEP` / `STABLE` |
| code_summary_type | `0` / `1` |
| few_shot | `0` / `1` |

  

## Stimulus generation agents

  
  

The stimulus generation agent that utilises LLM is defined in `./agents/agent_LLM.py`. It consists of five components:

- Prompt generator: for generating system messages, initial queries, and iterative queries according to different templates and DUTs.

- Defined in `./prompt_generators`.

- They specify the "_Missed-bin sampling_" methods.

- Stimulus generator: the LLM, which takes in a prompt together with previous conversation and responds with a text.

- Defined in `./models`. OpenAI's models and Llama 2 are provided.

- They specify the "_Best-iterative-message sampling_" methods and the "_Best-iterative-message resetting_" plans.

- Extractor: for extracting numbers from the text response.

- Defined in `./stimuli_extractor.py`

- Filter: for filtering out invalid numbers

- Defined in `./stimuli_filter.py`

- Loggers: for logging prompts, responses, and coverage over experiment trials.

- Defined in `./loggers`. CSV and TXT loggers are provided.

  

The "_Dialogue restarting_" plans are specified in `agent_LLM.py`.

  

Please refer to `generate_stimulus.py` files for how to create and use the stimulus generation agent.

  

## Open-source designs used

| Design | License |
|--|--|
| async_fifo [GitHub](https://github.com/dpretet/async_fifo) | All code under `async_fifo/src/` is released under the [MIT License](https://opensource.org/license/mit).|
| sdram_controller [GitHub](https://github.com/stffrdhrn/sdram-controller) | All code under `sdram_controller/src/` is released under the [BSD License](https://opensource.org/license/bsd-3-clause). |
| mips_cpu [GitHub](https://github.com/trivialmips/nontrivial-mips)| All code under `mips_cpu/src/` is released under the [MIT License](https://opensource.org/license/mit), with the exception of `mips_cpu/src/utils/fifo_v3.sv`, which is licensed under [The Solderpad Hardware Licence](https://solderpad.org/licenses/) (source code from [GitHub](https://github.com/pulp-platform/ariane)) |