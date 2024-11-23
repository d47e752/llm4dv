from prompt_generators.prompt_generator_template import *

BOUND = 64
class TemplatePromptGeneratorAG_WB(TemplatePromptGenerator):
    def __init__(
        self,
        dut_code_path: str = "",
        tb_code_path: str = "",
        bin_descr_path: str = "",
        code_summary_type: int = 0,  # 0: no code, 1: code
        sampling_missed_bins_method: Union[str, None] = None,
        few_shot: int = 0
    ):
        super().__init__(
            dut_code_path,
            tb_code_path,
            bin_descr_path,
            code_summary_type,
            sampling_missed_bins_method,
            100,
            few_shot
        )

    def generate_system_prompt(self) -> str:
        return (
            "Please output a list of positive integer pairs only, "
            f"each integer between 1 and {BOUND}. \n"
            f"Do not give any text - explanations, comments or any remarks - only the list of integers. \n"
            f"Output format: [(a,b),(c,d)...]."
        )

    def _load_introduction(self) -> str:
        if self.code_summary_type == 1:
            return (
                "You will receive code of a \"weight bank\" and a testbench for it, "
                "as well as a description of bins (i.e. test cases). "
                "The purpose of this device is to load data (weights) from RAM into a FIFO, then output them diagonally."
                "Then, you are going to generate a list of integer pairs to cover these test cases.\n"
            )
        elif self.code_summary_type == 0:
            return (
                "You will receive a description of bins (i.e. test cases) of a testbench for "
                "a hardware device under test (DUT), which is a weight bank." 
                "The purpose of this device is to load data (weights) from RAM into a FIFO, then output them diagonally."
                "Then, you are going to generate a list of integer pairs to cover these test cases.\n"
            )
        else:
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
            f"Now, we want to test the weight bank with a list of integer pairs as its input. "
            f"We want the input to cover the bins (i.e. test cases) that we care about. "
            f"Here's the description of the bins that we care about:\n"
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
                f"- (16,1) => 16 units of data loaded on each row, 1 row was loaded with valid data => in_1, out_1, combined_features_1_1 covered\n"
                f"- (32,5) => 32 units of data loaded on each row, 5 rows were loaded with valid data => in_2, out_5, combined_features_2_5 covered\n"
                f"- (64,3) => 64 units of data loaded on each row, 3 rows were loaded with valid data => in_4, out_3, combined_features_4_3 covered\n"
                f"- (64,41) => 64 units of data loaded on each row, 41 rows were loaded with valid data => in_4, out_41, combined_features_4_41 covered\n"
                f"- (1,22) => 16 units of data loaded on each row, 22 rows were loaded with valid data => in_1, out_22, combined_features_1_22 covered\n"
                f"------\n"  
            )
        else:
            examples = ""
        return examples

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
                f"Please generate a list of integer pairs, "
                f"each integer between 1 and {BOUND}, "
                "with output format: [(a,b),(c,d)...]"
                f"Here are {'some of ' if self.sampling_missed_bins else ''}the unreached bins:\n"
            )

        elif kwargs["no_new_hit"]:
            result_summary = (
                "The new values you just provided didn't cover any new bins. You need to try to cover as "
                "much of the described bins as you can.\n"
                "You will see the result coverage of your previous response(s), and then "
                "generate another list of integer pairs to cover the unreached bins (i.e. test cases)\n"
                "Do not give any text - explanations, comments or any remarks - only the list of integers.\n"
                f"Here are {'some of ' if self.sampling_missed_bins else ''} the unreached bins:\n"
            )

        else:
            result_summary = (
                "The values you provided failed to cover all the bins.\n"
                "You will see the result coverage of your previous response(s), and then "
                "generate another list of integer pairs to cover the unreached bins (i.e. test cases)\n"
                "Do not give any text - explanations, comments or any remarks - only the list of integers.\n"
                f"Here are {'some of ' if self.sampling_missed_bins else ''}the unreached bins:\n"
            )
        return result_summary

    def _load_coverage_difference_prompts_dict(self) -> Dict[str, str]:
        in_difference = {
            f"in_{i}": f"- {i*16} data loaded in each row is unreached.\n"
            for i in range(1, int(BOUND/16+1))
        }
        out_difference = {
            f"out_{i}": f"- {i} rows loaded with valid data is unreached.\n"
            for i in range(1, BOUND+1)
        }
        combined_difference = {
            f"combined_features_{i}_{j}": f"- {i*16} units of data loaded on each row, and {j} number of rows loaded with valid data is unreached,\n"
            for i in range(1, int(BOUND/16+1))
            for j in range(1, BOUND+1)
        }

        coverage_difference_template = {
            **in_difference,
            **out_difference,
            **combined_difference,
        }
        return coverage_difference_template

    def _load_iter_question(self, **kwargs) -> str:
        if kwargs["response_invalid"]:
            iter_question = (
                "Your response doesn't answer my query.\n"
                f"Please generate a list of integer pairs, "
                f"each integer between 1 and {BOUND}, "
                "with output format: [(a,b),(c,d)...]"
                "Do not give any text - explanations, comments or any remarks - only the list of integers.\n"
            )
        else:
            iter_question = (
                "Please regenerate integer pairs for the still unreached bins "
                "according to the BINS DESCRIPTION.\n"
                "Do not give any text - explanations, comments or any remarks - only the list of integers.\n"
            )
        return iter_question