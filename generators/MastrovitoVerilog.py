import datetime
import json
import logging
import pathlib
from logging.handlers import RotatingFileHandler
from pathlib import Path

from generators import Mastrovito

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
proj_path = pathlib.Path(__file__).resolve().parent.parent
handle = RotatingFileHandler(
    proj_path.joinpath("logs/mastrovitoverilog.log"), maxBytes=5 * 1024 * 1024, backupCount=3
)
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
)
handle.setFormatter(formatter)
logger.addHandler(handle)


class MastrovitoVerilogGenerator(Mastrovito.MastrovitoMatrixGenerator):
    """
    Class for transforming Mastrovito multiplication matrix into verilog zero latency multiply and add module.
    """

    def __init__(self):
        logger.info("Loading config")
        self._load_config()
        degree = None
        if self.config["gf_degree"] is not None:
            degree = self.config["gf_degree"]
        assert degree is not None

        irreducible_poly = None
        if len(self.config["irreducible_poly"]):
            irreducible_poly = self.config["irreducible_poly"]

        logger.info(
            f"Initializing Mastrovito matrix generator with degree {degree}"
            f" and irreducible polynomial {irreducible_poly}"
        )

        super().__init__(degree, irreducible_poly)

    def _load_config(self, path=None):
        path = pathlib.Path(__file__).parent.resolve() if path is None else path
        file_string = ""
        with Path.open(Path.joinpath(path, "config.json")) as file:
            file_string = file.read()
        self.config = json.loads(file_string)
        self.config["create_date"] = datetime.datetime.now()

    # Functions

    def _generate_mult_function_header(self, A, degree):
        self.func_name = f"GF2_Deg{degree}_const_mult_by_{A}"
        return (
            f"function automatic [{degree - 1}:0]{self.func_name};\n"
            + f"    input [{degree - 1}:0] Z;\n"
            + "    begin\n"
        )

    @staticmethod
    def _generate_mult_function_foot():
        return "    end\n" + "endfunction\n\n"

    def _generate_mult_function_body(self, mastrovito_matrix):
        output_str: str = ""
        for row_indx, mastr_row in enumerate(mastrovito_matrix):
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
            f"function automatic [{degree - 1}:0]GF2_Deg{degree}_add;\n"
            + f"    input [{degree - 1}:0] add1;\n"
            + f"    input [{degree - 1}:0] add2;\n"
            + "    begin\n"
            + "        return add1^add2;\n"
            + "    end\n"
            + "endfunction\n\n"
        )

    def _generate_all_functions(self, multiplicants):
        outstring = "//Generated Functions\n\n"

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

    def _generate_module_header(self):
        logger.info("Generating module header")
        return (
            f"module {self.config['design_name']}_Deg{self.config['gf_degree']} #\n"
            + "(\n"
            + "    parameter GF_CONST_MULT = 1\n"
            + ")\n"
            + "(\n"
            + f"    input wire [{self.gf_degree - 1}:0] B,\n"
            + f"    input wire [{self.gf_degree - 1}:0] C,\n"
            + f"    output wire [{self.gf_degree - 1}:0] PS\n"
            + ");\n"
            + "// P = GF_CONST_MULT*B "
            + "// PS = P + C\n"
            + "\n"
            + f"wire [{self.gf_degree - 1}:0]P;\n"
            + "\n"
        )

    @staticmethod
    def _generate_module_foot():
        return "\n" + "endmodule;\n"

    def _generate_module_body(self, multiplicants):
        logger.info("Generating module body")
        outstring = "generate\n" + "\n"

        for multiplicant in multiplicants:
            outstring += self._generate_mult_if(multiplicant, self.gf_degree)
        outstring += (
            "begin \t\t\t\t\t: generate_block_mult_INVALID\n"
            + '    $fatal("Not generated Constant Multiplicant Selected: %d.", GF_CONST_MULT);\n'
            + "end\n\n"
        )

        outstring += self._generate_sum_if(self.gf_degree)

        outstring += "endgenerate\n"

        return outstring

    def _generate_module(self, multiplicants):
        return (
            self._generate_module_header()
            + self._generate_all_functions(multiplicants)
            + self._generate_module_body(multiplicants)
            + self._generate_module_foot()
        )

    # File

    def _generate_file_header(self):
        return (
            f"{'//' * 20}\n"
            + f"// Company: {self.config['company']}\n"
            + f"// Engineer: {self.config['engineer']}\n"
            + f"// Create Date: {self.config['create_date']}\n"
            + f"// Design Name: {self.config['design_name']}_Deg{self.config['gf_degree']}\n"
            + f"// Project Name: {self.config['project_name']}\n"
            + f"// Description: {self.config['description']}\n"
            + f"// Dependencies: {self.config['dependencies']}\n"
            + "//\n"
            + "// Design Specific Parameters: \n"
            + f"// Irreducible Polynomial: {self.gf_field.irreducible_poly}\n"
            + f"// Degree: {self.gf_degree}\n"
            + f"// Constant Multiplicants: {self.config['constant_multplicants']}\n"
            + f"// Additional Comments: {self.config['additional_comments']}\n"
            + f"{'//' * 20} \n\r\n\r"
            + "`timescale 1ns/1ps"
        )

    def print_verilog_file(self):
        file_name = f"{self.config['design_name']}_Deg{self.config['gf_degree']}.v"

        path = proj_path.joinpath(self.config["path"])

        Path(path).mkdir(exist_ok=True, parents=True)

        multiplicants = self.config["constant_multplicants"]
        multiplicants.sort()

        with Path.open(pathlib.Path.joinpath(path, file_name), "w") as file:
            logger.info(f"Generating Verilog File: {path}")
            file.write(self._generate_file_header())

            file.write(self._generate_module(multiplicants))


if __name__ == "__main__":
    mastroVer = MastrovitoVerilogGenerator()

    mastroVer.print_verilog_file()
