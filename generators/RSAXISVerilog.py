import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Required

import numpy as np

from generators.ModuleVerilog import ModuleInterface, ModuleVerilogGenerator, ModuleVerilogParameters
from generators.RSAccumulatorVerilog import RSAccumulatorVerilogGenerator, RSAccumulatorVerilogParameters
from generators.RSSegmentVerilog import RSSegmentVerilogParameters


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


class RSAXISVerilogParameters(ModuleVerilogParameters):
    acc_params: Required[RSAccumulatorVerilogParameters]


class RSAXISVerilogGenerator(ModuleVerilogGenerator):
    def __init__(self, parameters: RSAXISVerilogParameters) -> None:
        self.params = parameters
        super().__init__(parameters)
        self._load_global_config()
        self.acc_verilog = RSAccumulatorVerilogGenerator(self.params["acc_params"])

    def _generate_module_header(self) -> str:
        word_size = self.params["acc_params"]["word_size"]
        interfaces = [
            (
                ModuleInterface("ACLK", "i"),
                ModuleInterface("ARESETn", "i"),
            ),
            (
                ModuleInterface("TVALID_m", "o"),
                ModuleInterface("TREADY_m", "i"),
                ModuleInterface("TDATA_m", "o", word_size),
                ModuleInterface("TLAST_m", "o"),
            ),
            (
                ModuleInterface("TVALID_s", "i"),
                ModuleInterface("TREADY_s", "o"),
                ModuleInterface("TDATA_s", "i", word_size),
                ModuleInterface("TLAST_s", "i"),
            ),
        ]
        return self.generic_generate_module_header(interfaces)

    def _generate_module_foot(self) -> str:
        return f"\nendmodule // {self.params['design_name']}\n"

    def _generate_accumulator_instance(self) -> str:
        template = self.acc_verilog.generic_generate_module_instance_template()
        return template.format(
            instance_name="",
            clk="ACLK",
            acc_input="TDATA_s",
            acc_output="acc_output",
            feedback="(!feedback_control_reg & TVALID_s)",
        )

    @staticmethod
    def _get_feedback_control_template():
        with open("generators/templates/rs_axis.txt", "r") as f:
            template = f.read()
        return template

    def _generate_feedback_control(self) -> str:
        template = self._get_feedback_control_template()
        return template.format(
            n_parity_max=self.acc_verilog.params["word_size"], word_size=self.acc_verilog.params["word_size"]
        )

    def _generate_module_body(self) -> str:
        return self._generate_feedback_control() + self._generate_accumulator_instance()

    def _generate_module(self, *args, **kwargs) -> str:
        return (
            self._generate_file_header()
            + self._generate_module_header()
            + self._generate_module_body()
            + self._generate_module_foot()
        )

    def generate_to_file(self):
        file_name = f"{self.params['design_name']}.v"

        path = proj_path.joinpath(self.params["output_path"])

        Path(path).mkdir(exist_ok=True, parents=True)

        with Path.open(Path.joinpath(path, file_name), "w") as file:
            logger.info(f"Generating Verilog File: {path}")
            file.write(self._generate_module())

    def generate(self):
        self.acc_verilog.generate()
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

    acc_params: RSAccumulatorVerilogParameters = {
        "design_name": "RS_Accumulator",
        "description": "",
        "output_path": Path("rtl"),
        "word_size": 10,
        "n_parity_sym": 10,
        "segment_generator_params": seg_params,
    }

    params: RSAXISVerilogParameters = {
        "design_name": "RS_AXIS",
        "description": "",
        "output_path": Path("rtl"),
        "acc_params": acc_params,
    }

    RSAcc = RSAXISVerilogGenerator(params)

    RSAcc.generate()
