import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import NotRequired, Required

import numpy as np

from generators.MastrovitoVerilog import MastrovitoVerilogGenerator, MastrovitoVerilogParameters

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
proj_path = Path(__file__).resolve().parent.parent
handle = RotatingFileHandler(
    proj_path.joinpath("logs/rs_verilog_segment.log"), maxBytes=5 * 1024 * 1024, backupCount=3
)
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
)
handle.setFormatter(formatter)
logger.addHandler(handle)


class RSSegmentVerilogParameters(MastrovitoVerilogParameters):
    constant_multplicants: Required[list[int]]


class RSSegmentVerilogGenerator(MastrovitoVerilogGenerator):
    def __init__(self, params: RSSegmentVerilogParameters):
        super().__init__(params)

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

    def _generate_module_header(self):
        logger.info("Generating module header")
        return (
            f"module {self.params['design_name']} #\n"
            + "(\n"
            + "    parameter GF_CONST_MULT = 1\n"
            + ")\n"
            + "(\n"
            + "    input wire clk,\n"
            + f"    input wire [{self.gf_degree - 1}:0]  RS_Backward_I,\n"
            + f"    output wire [{self.gf_degree - 1}:0] RS_Backward_O,\n"
            + f"    output wire [{self.gf_degree - 1}:0]  RS_Forward_O,\n"
            + f"    input wire [{self.gf_degree - 1}:0] RS_Forward_I\n"
            + ");\n"
            + "// RS_Backward_O = RS_Backward_I \n"
            + "// RS_Forward_O = RS_Backward_I * GF_CONST_MULT + RS_Forward_I\n"
            + "\n"
            + f"wire [{self.gf_degree - 1}:0]P;\n"
            + f"wire [{self.gf_degree - 1}:0]PS;\n"
            + f"reg  [{self.gf_degree - 1}:0]RS_Forward_O_reg = 0;"
            + "\n"
        )

    @staticmethod
    def _generate_module_synchronous():
        logger.info("Generating module header")
        return (
              "always @(posedge clk) begin : Latency_1\n"
            + "    RS_Forward_O_reg <= PS;\n"
            + "end // always\n"
            + "\n"
        )
    
    def _generate_module_foot(self) -> str:
        return (
            "assign RS_Forward_O = RS_Forward_O_reg;\n"
            + "assign RS_Backward_O = RS_Backward_I;\n"
            + "\n"
            + "endmodule\n"
        )
    
    def _generate_module(self, multiplicants):
        return (
            self._generate_module_header()
            + self._generate_all_functions(multiplicants)
            + self._generate_module_body(multiplicants)
            + self._generate_module_synchronous()
            + self._generate_module_foot()
        )
        

if __name__ == "__main__":
    params: RSSegmentVerilogParameters = {
        "design_name": "RS_Segment",
        "description": "Zero latency backward and one latency forwards building block "
            + "of RS encoder accumulator type",
        "gf_degree": 10,
        "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
        "output_path": Path("rtl"),
        "constant_multplicants": [0, 1, 2, 1023, 195, 175, 677, 918, 464, 463, 997, 498, 169]
    }
    mastroVer = RSSegmentVerilogGenerator(params)

    mastroVer.print_verilog_file()