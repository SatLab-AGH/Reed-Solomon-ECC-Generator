import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Required

import numpy as np
import reedsolo as rs

from generators.MastrovitoMatrix import MastrovitoMatrixGenerator
from generators.ModuleVerilog import ModuleInterface, ModuleVerilogGenerator, ModuleVerilogParameters
from generators.RSSegmentVerilog import RSSegmentVerilogGenerator, RSSegmentVerilogParameters

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
proj_path = Path(__file__).resolve().parent.parent
handle = RotatingFileHandler(
    proj_path.joinpath("logs/accumulatorverilog.log"), maxBytes=5 * 1024 * 1024, backupCount=3
)
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
)
handle.setFormatter(formatter)
logger.addHandler(handle)


class RSAccumulatorVerilogParameters(ModuleVerilogParameters):
    word_size: Required[int]
    n_parity_sym: Required[int]
    segment_generator_params: Required[RSSegmentVerilogParameters]


class RSAccumulatorVerilogGenerator(ModuleVerilogGenerator):
    def __init__(self, params: RSAccumulatorVerilogParameters):
        self.params = params
        super().__init__(params)
        self._load_global_config()

        # init field first, then update coeffs
        self.segment_generator = RSSegmentVerilogGenerator(params["segment_generator_params"])
        self.segment_generator.params["constant_multplicants"] = self.get_rs_generator_poly(
            self.segment_generator, params["n_parity_sym"]
        )
        logger.info(f"Generator polynomial: {self.segment_generator.params['constant_multplicants']}")
        self.params["specific_params"] = (
            f"\n//    Generator polynomial: {self.segment_generator.params['constant_multplicants']}\n"
        )

    @staticmethod
    def get_rs_generator_poly(mastrovito_matrix_generator: MastrovitoMatrixGenerator, n_parity_sym: int):
        gf_poly_coeffs = mastrovito_matrix_generator.irreducible_poly._integer
        rs.init_tables(gf_poly_coeffs, c_exp=mastrovito_matrix_generator.gf_degree)
        return list(rs.rs_generator_poly(n_parity_sym))

    def _generate_module_header(self) -> str:
        logger.info("Generating module header")
        word_size = self.params["word_size"]
        n_parity = self.params["n_parity_sym"]

        # 1. Define the port interfaces
        interfaces = [
            (
                ModuleInterface("clk", "i"),
                ModuleInterface("rst_n", "i"),
                ModuleInterface("acc_input", "i", word_size),
                ModuleInterface("acc_output", "o", word_size),
                ModuleInterface("feedback", "i"),
            )
        ]

        # 2. Generate the standard header string via the generic method
        return self.generic_generate_module_header(interfaces)

    def _generate_module_top_logic(self) -> str:
        word_size = self.params["word_size"]
        return (
            "\n"
            + f"wire [{word_size - 1}:0] BackwardBus[{self.params['n_parity_sym']}:0];\n"
            + f"wire [{word_size - 1}:0] ForwardBus[{self.params['n_parity_sym']}:0];\n"
            + f"wire [{word_size - 1}:0] backXORforw;\n"
            + "\n"
            + "assign backXORforw = feedback ? acc_input ^ acc_output : 0;\n"
            + "\n"
        )

    def _generate_module_foot(self) -> str:  # noqa: PLR6301
        return "\n" + "endmodule\n"

    def _generate_module_body(self):
        word_size = self.params["word_size"]
        module_body: str = ""
        gen_coefs = self.segment_generator.params["constant_multplicants"]
        bi = None
        bo = None
        fi = None
        fo = None
        for idx, coef in enumerate(gen_coefs[1:]):
            bi = f"BackwardBus[{idx - 1}]"
            bo = f"BackwardBus[{idx}]"
            fi = f"ForwardBus[{idx}]"
            fo = f"ForwardBus[{idx - 1}]"
            if idx == 0:
                bi = "backXORforw"
                fo = "acc_output"

            template = self.segment_generator.generic_generate_module_instance_template()

            module_body += template.format(
                instance_name=f"{idx}",
                GF_CONST_MULT=coef,
                clk="clk",
                rst_n="rst_n",
                RS_Backward_I=bi,
                RS_Backward_O=bo,
                RS_Forward_I=fi,
                RS_Forward_O=fo,
            )

        module_body += f"// polynomial coeff 1\nassign ForwardBus[{len(gen_coefs) - 2}] = 0;\n\n"

        return module_body

    def _generate_module(self):
        return (
            self._generate_module_header()
            + self._generate_module_top_logic()
            + self._generate_module_body()
            + self._generate_module_foot()
        )

    def generate(self):
        self.segment_generator.generate_to_file()
        self.generate_to_file()


if __name__ == "__main__":
    seg_params: RSSegmentVerilogParameters = {
        "design_name": "RS_Segment",
        "description": "Zero latency backward and one latency forwards building block "
        + "of RS encoder accumulator type",
        "gf_degree": 10,
        "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
        "output_path": Path("rtl"),
        "constant_multplicants": [0],  # To populate in init
    }

    params: RSAccumulatorVerilogParameters = {
        "design_name": "RS_Accumulator",
        "description": "",
        "output_path": Path("rtl"),
        "word_size": 10,
        "n_parity_sym": 10,
        "segment_generator_params": seg_params,
    }
    RSAcc = RSAccumulatorVerilogGenerator(params)

    RSAcc.generate()
