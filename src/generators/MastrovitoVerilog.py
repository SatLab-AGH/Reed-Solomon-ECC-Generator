from copy import copy, deepcopy
import logging
import pathlib
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import NotRequired, Required

import numpy as np
from numpy.typing import NDArray

from generators.MastrovitoMatrix import MastrovitoMatrixGenerator, MastrovitoMatrixParameters
from generators.ModuleVerilog import (
    ModuleInterface,
    ModuleParameter,
    ModuleVerilogGenerator,
    ModuleVerilogParameters,
)
from generators.logging_config import setup_logging

logger = logging.getLogger(__name__)
proj_path = Path(__file__).resolve().parent.parent


class MastrovitoVerilogParameters(ModuleVerilogParameters, MastrovitoMatrixParameters):
    constant_multplicants: NotRequired[list[int]]


class MastrovitoVerilogGenerator(MastrovitoMatrixGenerator, ModuleVerilogGenerator):
    """
    Class for transforming Mastrovito multiplication matrix into verilog zero latency multiply and add module.
    """

    def __init__(self, params: MastrovitoVerilogParameters):
        logger.info("Loading config")
        self.params = params
        MastrovitoMatrixGenerator.__init__(self, params)
        ModuleVerilogGenerator.__init__(self, params)
        self._load_global_file_config()
        self.design_name = f"GF_Mastrovito_Multiplier_Adder_Deg{params['gf_degree']}"
        self.description = f"Zero latency, combinatorial galois field multiplier-adder (A*B+C) implemented as XOR Mastrovito matrix with predefined A."
        self.params["specific_params"] = (
            f"\n//    gf_degree: {self.params['gf_degree']}"
            f"\n//    gf irreducible_poly_coeffs: {self.params['irreducible_poly_coeffs']}"
            f"\n//    available multplicants: {self.params.get('constant_multplicants')}"
        )

        logger.info(
            f"Initializing Mastrovito matrix generator with degree {params['gf_degree']}"
            f" and irreducible polynomial {params['irreducible_poly_coeffs']}"
        )

    # Functions

    def _generate_mult_function_header(self, A, degree):
        self.func_name = f"GF2_Deg{degree}_const_mult_by_{A}"
        return (
            f"function [{degree - 1}:0]{self.func_name};\n"
            + f"    input [{degree - 1}:0] Z;\n"
            + "    begin\n"
        )

    @staticmethod
    def _generate_mult_function_foot():
        return "    end\n" + "endfunction\n\n"

    def _generate_mult_function_body(self, mastrovito_matrix: NDArray):
        output_str: str = ""
        for row_indx, mastr_row_matrix in enumerate(mastrovito_matrix):
            mastr_row = np.array(mastr_row_matrix).flatten()
            output_line_head: str = f"        {self.func_name}[{row_indx}] = "
            output_line_body: str = ""
            for col_indx, mastr_elem in enumerate(mastr_row):
                if mastr_elem:
                    if len(output_line_body.strip()):
                        output_line_body += " ^ "
                    output_line_body += f"Z[{col_indx}]"
                else:
                    # Makes output xor'ing matrixlike alligned
                    output_line_body += f"  {' ' * len(str(col_indx))} "
                    output_line_body += "   "
            if not any(mastr_row):
                output_line_body = "0"

            output_str += output_line_head + output_line_body + ";\n"

        return output_str

    def _generate_mult_function(self, A) -> str:
        mastrovito_matrix = self.get_mastrovito(A)
        verilog_function_string: str = self._generate_mult_function_header(A, self.gf_degree)
        verilog_function_string += self._generate_mult_function_body(mastrovito_matrix)
        verilog_function_string += self._generate_mult_function_foot()

        return verilog_function_string

    @staticmethod
    def _generate_add_function(degree) -> str:
        return (
            f"function [{degree - 1}:0]GF2_Deg{degree}_add;\n"
            + f"    input [{degree - 1}:0] add1;\n"
            + f"    input [{degree - 1}:0] add2;\n"
            + "    begin\n"
            + f"        GF2_Deg{degree}_add=add1^add2;\n"
            + "    end\n"
            + "endfunction\n\n"
        )

    def _generate_all_functions(self, multiplicants):
        outstring = "//Generated Functions\n\n"
        multiplicants = list(set(multiplicants))
        multiplicants.sort()

        outstring += self._generate_add_function(self.gf_degree)

        for multiplicant in multiplicants:
            outstring += self._generate_mult_function(multiplicant)

        return outstring

    # Verilog function calls generation
    @staticmethod
    def _generate_mult_if(A, degree):
        return (
            f"if(GF_CONST_MULT == {A}) begin \t\t\t: generate_block_mult_{A}\n"
            + f"    assign P = GF2_Deg{degree}_const_mult_by_{A}(B);\n"
            + "end else "
        )

    @staticmethod
    def _generate_sum_if(degree):
        return "\n" + f"assign PS = GF2_Deg{degree}_add(P, C);\n" + "\n"

    # Module

    def _generate_module_header(self) -> str:
        logger.info("Generating module header")
        degree = self.gf_degree

        interfaces = [
            (
                ModuleInterface("B", "i", degree),
                ModuleInterface("C", "i", degree),
                ModuleInterface("PS", "o", degree),
            )
        ]
        parameters = [ModuleParameter("GF_CONST_MULT", default_value=1)]
        ports_code = self.generic_generate_module_header(interfaces, parameters)

        return f"{ports_code}// P = GF_CONST_MULT*B\n// PS = P + C\n\nwire [{degree - 1}:0] P;\n\n"

    def _generate_module_foot(self) -> str:  # noqa: PLR6301
        return "\n" + "endmodule\n"

    def _generate_module_body(self, multiplicants):
        logger.info("Generating module body")
        outstring = "generate\n" + "\n"

        multiplicants = list(set(multiplicants))

        for multiplicant in multiplicants:
            outstring += self._generate_mult_if(multiplicant, self.gf_degree)
        outstring += (
            "begin \t\t\t\t\t: generate_block_mult_INVALID\n"
            + '    $fatal("Not generated Constant Multiplicant Selected: %d.", GF_CONST_MULT);\n'
            + "end\n\n"
        )

        outstring += self._generate_sum_if(self.gf_degree)

        outstring += "endgenerate\n\n"

        return outstring

    def _generate_module(self):
        multiplicants = deepcopy(self.params["constant_multplicants"])
        multiplicants.sort()
        return (
            self._generate_module_header()
            + self._generate_all_functions(multiplicants)
            + self._generate_module_body(multiplicants)
            + self._generate_module_foot()
        )


if __name__ == "__main__":
    setup_logging(f"MastrovitoVerilog/default.log")
    params: MastrovitoVerilogParameters = {
        "gf_degree": 10,
        "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
        "constant_multplicants": [0, 1, 2, 6, 511, 513, 1023],
    }
    mastroVer = MastrovitoVerilogGenerator(params)

    mastroVer.generate_to_dir()
