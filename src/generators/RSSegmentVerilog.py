import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import NotRequired, Required, override

import numpy as np

from generators.MastrovitoVerilog import MastrovitoVerilogGenerator, MastrovitoVerilogParameters
from generators.ModuleVerilog import ModuleInterface, ModuleParameter
from generators.logging_config import setup_logging

logger = logging.getLogger(__name__)


class RSSegmentVerilogParameters(MastrovitoVerilogParameters):
    pass


class RSSegmentVerilogGenerator(MastrovitoVerilogGenerator):
    def __init__(self, params: RSSegmentVerilogParameters):
        super().__init__(params)
        self.description = (
            f"One cycle latency galois field multiplier-adder (A*B+C) implemented as XOR Mastrovito matrix with predefined A.\n"
            "//\t\t\tImplemented Backward bypass for Reed-Solomon encoder implementation."
        )
        self.design_name = "RS_Segment"

    # Verilog function calls generation
    @staticmethod
    def _generate_mult_if(A, degree):
        return (
            f"if(GF_CONST_MULT == {A}) begin \t\t\t: generate_block_mult_{A}\n"
            + f"    assign P = GF2_Deg{degree}_const_mult_by_{A}(RS_Backward_I);\n"
            + "end else "
        )

    @staticmethod
    def _generate_sum_if(degree):
        return "\n" + f"assign PS = GF2_Deg{degree}_add(P, RS_Forward_I);\n" + "\n"

    def _generate_module_header(self) -> str:
        parameters = [ModuleParameter(str("GF_CONST_MULT"), None, 1)]
        interfaces = [
            (
                ModuleInterface("clk", "i"),
                ModuleInterface("rst_n", "i"),
                ModuleInterface("RS_Backward_I", "i", self.gf_degree),
                ModuleInterface("RS_Backward_O", "o", self.gf_degree),
                ModuleInterface("RS_Forward_O", "o", self.gf_degree),
                ModuleInterface("RS_Forward_I", "i", self.gf_degree),
            )
        ]
        return self.generic_generate_module_header(interfaces, parameters)

    def _generate_net(self):
        logger.info("Generating module header")
        return (
            f"wire [{self.gf_degree - 1}:0]P;\n"
            + f"wire [{self.gf_degree - 1}:0]PS;\n"
            + f"reg  [{self.gf_degree - 1}:0]RS_Forward_O_reg = 0;"
            + "\n"
        )

    @staticmethod
    def _generate_module_synchronous():
        logger.info("Generating module header")
        return (
            "always @(posedge clk) begin : Latency_1\n"
            + "    RS_Forward_O_reg <= rst_n ? PS : 0;\n"
            + "end // always\n"
            + "\n"
        )

    @override
    def _generate_module_foot(self) -> str:
        return (
            "assign RS_Forward_O = RS_Forward_O_reg;\n"
            + "assign RS_Backward_O = RS_Backward_I;\n"
            + "\n"
            + "endmodule\n"
        )

    def _generate_module(self):
        multiplicants = self.params["constant_multplicants"]
        return (
            self._generate_module_header()
            + self._generate_net()
            + self._generate_all_functions(multiplicants)
            + self._generate_module_body(multiplicants)
            + self._generate_module_synchronous()
            + self._generate_module_foot()
        )


if __name__ == "__main__":
    setup_logging(f"RS_Segment/default.log")
    params: RSSegmentVerilogParameters = {
        "gf_degree": 10,
        "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
        "constant_multplicants": [0, 1, 2, 1023, 195, 175, 677, 918, 464, 463, 997, 498, 169],
    }
    mastroVer = RSSegmentVerilogGenerator(params)

    mastroVer.generate_to_dir()
