import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

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
    pass


class RSSegmentVerilogGenerator(MastrovitoVerilogGenerator):
    def __init__(self, params: RSSegmentVerilogParameters):
        super().__init__(params)

    def _generate_module_header(self):
        logger.info("Generating module header")
        return (
            f"module {self.config['design_name']}_Deg{self.config['gf_degree']} #\n"
            + "(\n"
            + "    parameter GF_CONST_MULT = 1\n"
            + ")\n"
            + "(\n"
            + "    input wire clk,\n"
            + f"    input wire [{self.gf_degree - 1}:0]  RS_Backward_I,\n"
            + f"    output wire [{self.gf_degree - 1}:0] RS_Backward_O,\n"
            + f"    input wire [{self.gf_degree - 1}:0]  RS_Forward_O,\n"
            + f"    output wire [{self.gf_degree - 1}:0] RS_Forward_I,\n"
            + ");\n"
            + "// RS_Backward_O = RS_Backward_I \n"
            + "// RS_Forward_O = RS_Backward_I * GF_CONST_MULT + RS_Forward_I\n"
            + "\n"
            + f"wire [{self.gf_degree - 1}:0]P;\n"
            + f"wire [{self.gf_degree - 1}:0]PS;\n"
            + f"reg  [{self.gf_degree - 1}:0]RS_Forward_O_reg;"
            + "\n"
        )

    @staticmethod
    def _generate_module_synchronous():
        logger.info("Generating module header")
        return (
              "always @(posedge clk) begin\n"
            + "    RS_Forward_O_reg <= PS;\n"
            + "end // always\n"
            + "\n"
        )
    
    @staticmethod
    def _generate_module_foot() -> str:
        return (
            "assign RS_Forward_O = RS_Forward_O_reg;\n"
            + "\n"
            + "endmodule;\n"
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
        "degree": 10,
        "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
        "output_path": Path("rtl"),
        "constant_multplicants": [0, 1, 2, 6, 511, 513, 1023]
    }
    mastroVer = RSSegmentVerilogGenerator(params)

    mastroVer.print_verilog_file()