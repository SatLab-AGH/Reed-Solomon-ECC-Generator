import logging
from logging.handlers import RotatingFileHandler
import unittest
import Mastrovito
import json
import datetime
import os
import pathlib

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
proj_path = pathlib.Path(__file__).resolve().parent.parent
handle = RotatingFileHandler(proj_path.joinpath("logs/mastrovitoverilog.log"), maxBytes=5 * 1024 * 1024, backupCount=3)
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s'
)
handle.setFormatter(formatter)
logger.addHandler(handle)

class MastrovitoVerilog(Mastrovito.MastrovitoMatrixGenerator):
    """
    Class for transforming Mastrovito multiplication matrix into verilog zero latency multiply and add module.
    """
    def __init__(self):
        logger.info("Loading config")
        self._load_config()
        if self.config["gf_degree"] is not None:
            degree = self.config["gf_degree"]
            
        irreducible_poly = None
        if len(self.config["irreducible_poly"]):
            irreducible_poly = self.config["irreducible_poly"]

        logger.info(f"Initializing Mastrovito matrix generator with degree {degree} and irreducible polynomial {irreducible_poly}")

        super().__init__(degree, irreducible_poly)
        
    def _load_config(self, path = pathlib.Path(__file__).parent.resolve()):
        file_string = ''
        with open(pathlib.Path.joinpath(path, "config.json"), "r") as file:
            file_string = file.read()
        self.config = json.loads(file_string)
        self.config["create_date"] = datetime.datetime.now()

    # Functions
    
    def _generate_mult_function_header(self, A, degree):
        self.func_name = f'GF2_Deg{degree}_const_mult_by_{A}'
        return \
            f'function automatic [{degree-1}:0]{self.func_name};\n' + \
            f'    input [{degree-1}:0] Z;\n' + \
            f'    begin\n'
    
    def _generate_mult_function_foot(self):
        return \
            f'    end\n' + \
            f'endfunction\n\n'
                
    def _generate_mult_function_body(self, mastrovito_matrix):
        output_str: str = str()
        for row_indx, mastr_row in enumerate(mastrovito_matrix):
            output_line_head: str = f"        {self.func_name}[{row_indx}] = "
            output_line_body:str = ""
            for col_indx, mastr_elem in enumerate(mastr_row):
                if mastr_elem:
                    if len(output_line_body.strip()):
                        output_line_body += f" ^ "
                    output_line_body += f'Z[{col_indx}]'
                else:
                    # Makes output xor'ing matrixlike alligned
                    output_line_body += f'  {" " * len(str(col_indx))} '
                    output_line_body += f"   "
                    
            output_str += output_line_head + output_line_body + ";\n"
            
        return output_str
    
    def _generate_mult_function(self, A) -> str:
        
        mastrovito_matrix = self.get_mastrovito(A)
        verilog_function_string: str = self._generate_mult_function_header(self.A, self.gf_degree)
        verilog_function_string += self._generate_mult_function_body(mastrovito_matrix)
        verilog_function_string += self._generate_mult_function_foot()
        
        return verilog_function_string
    
    def _generate_add_function(self, degree) ->str:
        return f'function automatic [{degree-1}:0]GF2_Deg{degree}_add;\n' + \
        f'    input [{degree-1}:0] add1;\n' + \
        f'    input [{degree-1}:0] add2;\n' + \
        f'    begin\n' + \
        f'        return add1^add2;\n' + \
        f'    end\n' + \
        f'endfunction\n\n'
    
    def _generate_all_functions(self, multiplicants):
        outstring = f'//Generated Functions\n\n'
        
        outstring += self._generate_add_function(self.gf_degree)

        for multiplicant in multiplicants:
                outstring += self._generate_mult_function(multiplicant)

        return outstring
    
    # Verilog function calls generation

    def _generate_mult_if(self, A, degree):
        return \
        f'if(GF_CONST_MULT == {A}) begin \t\t\t: generate_block_mult_{A}\n' + \
        f'    assign P = GF2_Deg{degree}_const_mult_by_{A}(B);\n' + \
        f'end else '

    
    def _generate_sum_if(self, degree):
        return \
        f'\n' + \
        f'assign PS = GF2_Deg{degree}_add(P, C);\n' + \
        f'\n'

    # Module

    def _generate_module_header(self):
        logger.info("Generating module header")
        return \
            f'module {self.config["design_name"]}_Deg{self.config["gf_degree"]} #\n' + \
            f'(\n' + \
            f'    parameter GF_CONST_MULT = 1\n' + \
            f')\n' + \
            f'(\n' + \
            f'    input wire [{self.gf_degree-1}:0] B,\n' + \
            f'    input wire [{self.gf_degree-1}:0] C,\n' + \
            f'    output wire [{self.gf_degree-1}:0] PS\n' + \
            f');\n' + \
            f'// P = GF_CONST_MULT*B ' + \
            f'// PS = P + C\n' + \
            f'\n' + \
            f'wire [{self.gf_degree-1}:0]P;\n' + \
            f'\n'

    
    def _generate_module_foot(self):
        return \
            f'\n' + \
            f'endmodule;\n'
    
    def _generate_module_body(self, multiplicants):
        logger.info("Generating module body")
        outstring = \
            f'generate\n' + \
            f'\n'


        for multiplicant in multiplicants:
            outstring += self._generate_mult_if(multiplicant, self.gf_degree)
        outstring += \
            f'begin \t\t\t\t\t: generate_block_mult_INVALID\n' + \
            f'    $fatal("Not generated Constant Multiplicant Selected: %d.", GF_CONST_MULT);\n' + \
            f'end\n\n'

        outstring += self._generate_sum_if(self.gf_degree)

        outstring += \
            f'endgenerate\n'

        return outstring

    def _generate_module(self, multiplicants):
        return \
        self._generate_module_header() + \
        self._generate_all_functions(multiplicants) + \
        self._generate_module_body(multiplicants) + \
        self._generate_module_foot()

    #File

    def _generate_file_header(self):
        return \
            f'{"//" * 20}\n' + \
            f'// Company: {self.config["company"]}\n' + \
            f'// Engineer: {self.config["engineer"]}\n' + \
            f'// Create Date: {self.config["create_date"]}\n' + \
            f'// Design Name: {self.config["design_name"]}_Deg{self.config["gf_degree"]}\n' + \
            f'// Project Name: {self.config["project_name"]}\n' + \
            f'// Description: {self.config["description"]}\n' + \
            f'// Dependencies: {self.config["dependencies"]}\n' + \
            f'//\n' + \
            f'// Design Specific Parameters: \n' + \
            f'// Irreducible Polynomial: {self.gf_field.irreducible_poly}\n' + \
            f'// Degree: {self.gf_degree}\n' + \
            f'// Constant Multiplicants: {self.config["constant_multplicants"]}\n' + \
            f'// Additional Comments: {self.config["additional_comments"]}\n' + \
            f'{"//" * 20} \n\r\n\r'
    
    def print_verilog_file(self):
        file_name = f'{self.config["design_name"]}_Deg{self.config["gf_degree"]}.v'

        path = proj_path.joinpath(self.config["path"])
        
        os.makedirs(path, exist_ok=True)
        
        multiplicants = self.config["constant_multplicants"]
        multiplicants.sort()
            
        with open(pathlib.Path.joinpath(path, file_name), 'w') as file:
            
            logger.info(f"Generating Verilog File: {path}")
            file.write(self._generate_file_header())
            
            file.write(self._generate_module(multiplicants))
            
if __name__ == '__main__':
    
    mastroVer = MastrovitoVerilog()

    mastroVer.print_verilog_file()