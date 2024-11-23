from prompt_generators.prompt_generator_template import *

BOUND = 64
class TemplatePromptGeneratorAG_FT(TemplatePromptGenerator):
    def __init__(
        self,
        dut_code_path: str = "../examples_SD/dut_code.txt",
        tb_code_path: str = "../examples_SD/tb_code.txt",
        bin_descr_path: str = "../examples_SD/bins_description.txt",
        code_summary_type: int = 0,  # 0: no code, 1: code, 2: summary
        sampling_missed_bins_method: Union[str, None] = None,
    ):
        super().__init__(
            dut_code_path,
            tb_code_path,
            bin_descr_path,
            code_summary_type,
            sampling_missed_bins_method,
        )

    def generate_system_prompt(self) -> str:
        return (
            "Please provide a list of lists, in the format: [[string, int, int, int], [string, int, int, int], ...]. "
            f"Any text outside this format is not allowed.\n"
            f"The first integer should be between 0 and 63, the other two between 0 and 1023.\n"
            f"Example: [[allocate, 15, 64, 0], [adjacency_write, 15, 1, 48]]\n"
            f"Do NOT provide any comments, extra remarks, context - only provide a list"
        )

    def _load_introduction(self) -> str:
        if self.code_summary_type == 1:
            return (
                "You will receive code of a DUT and a testbench for it, "
                "as well as a description of bins (i.e. test cases). "
                "The purpose of this device is to load data on three different queues: "
                "an \"adjacency queue\" (depth: 64), a \"message queue\" (depth: 4096), and a \"scale factor queue\" (depth: 64)\n"
            )
        elif self.code_summary_type == 0:
            return (
                "You will receive a description of bins (i.e. test cases) of a testbench for "
                "a hardware device under test (DUT).\n" 
                "The purpose of this device is to load data on three different queues: an \"adjacency queue\" (depth: 64), a \"message queue\" (depth: 4096), and a \"scale factor queue\" (depth: 64)\n"
            )
        else:
            # TODO: intro for code summaries
            raise NotImplementedError

    def _load_code_summary(self, dut_code_path, tb_code_path) -> str:
        if self.code_summary_type == 0:
            return ""
        elif self.code_summary_type == 1:
            with open(dut_code_path, "r") as f:
                dut_code = f.read()
            with open(tb_code_path, "r") as f:
                tb_code = f.read()
            dut_summary = (
                f"I have a device under test (DUT). Here's the SystemVerilog code of the DUT:\n"
                f"------\n"
                f"DUT CODE\n"
                f"{dut_code}\n"
                f"------\n"
                # f"I also have a testbench for the DUT. Here's the Python code of the testbench:\n"
                # f"------\n"
                # f"TESTBENCH CODE\n"
                # f"{tb_code}\n"
                # f"------\n"
            )
            return dut_summary
        else:
            # TODO: code summaries
            raise NotImplementedError

    def _load_bins_summary(self, bin_descr_dir, **kwargs) -> str:
        with open(bin_descr_dir, "r") as f:
            bins_description = f.read()
        tb_summary = (
            f"Now, we want to test the DUT with a list of commands as its input. "
            f"We want the input to cover the bins (i.e. test cases) that we care about. "
            f"Here's the description of the bins that we care about:\n"
            f"------\n"
            f"BINS DESCRIPTION\n"
            f"{bins_description}\n"
            f"------\n"
        )
        return tb_summary

    def _load_init_question(self) -> str:
        init_question = (
            "Following the bins description"
            + (", and refer to the programs" if self.code_summary_type != 0 else "")
            + ", generate a list of integer pairs "
            "which covers the described bins as much as you can.\n"
        )
        return init_question

    def _load_result_summary(self, **kwargs) -> str:
        if kwargs["response_invalid"]:
            result_summary = (
                "Your response doesn't answer my query. \n"
                f"Please provide a list of lists, in the format: [[string, int, int, int], [string, int, int, int], ...]."
                f"Example: [[deallocate, 0, 0, 0], [allocate, 15, 64, 0]]"
                f"Any text outside this format is not allowed."
                f"Do NOT provide any comments, extra remarks, context - only provide a list"
                f"Here are {'some of ' if self.sampling_missed_bins else ''}the unreached bins:\n"
            )

        elif kwargs["no_new_hit"]:
            result_summary = (
                "The new values you just provided didn't cover any new bins. You need to try to cover as "
                "much of the described bins as you can.\n"
                "You will see the result coverage of your previous response(s), and then "
                "generate another list of integer pairs to cover the unreached bins (i.e. test cases).\n"
                f"Do NOT provide any comments, extra remarks, context - only provide a list.\n"
                f"Here are {'some of ' if self.sampling_missed_bins else ''} the unreached bins:\n"
            )

        else:
            result_summary = (
                "The values you provided failed to cover all the bins.\n"
                "You will see the result coverage of your previous response(s), and then "
                "generate another list of integer pairs to cover the unreached bins (i.e. test cases).\n"
                f"Do NOT provide any comments, extra remarks, context - only provide a list.\n"
                f"Here are {'some of ' if self.sampling_missed_bins else ''}the unreached bins:\n"
            )
        return result_summary

    def _load_coverage_difference_prompts_dict(self) -> Dict[str, str]:
        coverage_difference_template = {
            f"adj_dealloc": f"the DUT is instructed to load the \"adjacency queue\", but the DUT was not allocated a \"nodeslot\"\n",
            f"mess_dealloc": f"the DUT is instructed to load the \"message queue\", but the DUT was not allocated a \"nodeslot\"\n",
            f"scale_dealloc": f"the DUT is instructed to load the \"scale factor queue\", but the DUT was not allocated a \"nodeslot\"\n",
            f"adj_nomatch": f"the DUT is instructed to load the \"adjacency queue\", but the \"nodeslot\" provided for this command does not match the \"nodeslot\" allocated to the DUT\n",
            f"mess_nomatch": f"the DUT is instructed to load the \"message queue\", but the \"nodeslot\" provided for this command does not match the \"nodeslot\" allocated to the DUT\n",
            f"scale_nomatch": f"the DUT is instructed to load the \"scale factor queue\", but the \"nodeslot\" provided for this command does not match the \"nodeslot\" allocated to the DUT\n",
            f"mess_fetch_adj_nopartial": f"the DUT is instructed to load the \"message queue\", and there is no overflow on the \"adjacency queue\"\n",
            f"mess_fetch_adj_partial": f"the DUT is instructed to load the \"message queue\", and there is overflow on the \"adjacency queue\"\n",
            f"mess_seen": f"data is loaded on the \"message queue\"\n",
            f"scale_seen": f"data is loaded on the \"scale queue\"\n",
        }
        return coverage_difference_template

    def _load_iter_question(self, **kwargs) -> str:
        if kwargs["response_invalid"]:
            iter_question = (
                "Your response doesn't answer my query.\n"
                "Please provide a list of lists, in the format: [[string, int, int, int], [string, int, int, int], ...]."
                f"Example: [[deallocate, 0, 0, 0], [allocate, 15, 64, 0]]"
                f"Any text outside this format is not allowed.\n"
                f"Do NOT provide any comments, extra remarks, context - only provide a list"
            )
        else:
            iter_question = (
                "Please regenerate commands for the still unreached bins "
                "according to the BINS DESCRIPTION.\n"
                f"Do NOT provide any comments, extra remarks, context - only provide a list"
            )
        return iter_question