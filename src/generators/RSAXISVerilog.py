import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Required

import numpy as np

from generators.ModuleVerilog import ModuleInterface, ModuleVerilogGenerator, ModuleVerilogParameters
from generators.RSAccumulatorVerilog import RSAccumulatorVerilogGenerator, RSAccumulatorVerilogParameters
from generators.RSSegmentVerilog import RSSegmentVerilogParameters


logger = logging.getLogger(__name__)
proj_path = Path(__file__).resolve().parent.parent


class RSAXISVerilogParameters(ModuleVerilogParameters):
    acc_params: Required[RSAccumulatorVerilogParameters]


class RSAXISVerilogGenerator(ModuleVerilogGenerator):
    def __init__(self, parameters: RSAXISVerilogParameters) -> None:
        self.params = parameters
        super().__init__(parameters)
        self.acc_verilog = RSAccumulatorVerilogGenerator(self.params["acc_params"])
        self.design_name = "RS_AXIS"
        self.description = (
            "AXI stream module, appends arbitrary RS checksum to AXI stream data after TLAST_s signal is asserted.\n"
            "//\t\t\t AXI stream data length control for RS utilization is user duty, checksum length is fixed."
        )
        self.dependencies = "RSAccumulatorVerilogGenerator, RSSegmentVerilogGenerator"

    def _generate_module_header(self) -> str:
        word_size = self.params["acc_params"]["word_size"]
        interfaces = [
            (
                ModuleInterface("aclk", "i"),
                ModuleInterface("areset_n", "i"),
            ),
            (
                ModuleInterface("axis_m_tvalid", "o"),
                ModuleInterface("axis_m_tready", "i"),
                ModuleInterface("axis_m_tdata", "o", word_size),
                ModuleInterface("axis_m_tlast", "o"),
            ),
            (
                ModuleInterface("axis_s_tvalid", "i"),
                ModuleInterface("axis_s_tready", "o"),
                ModuleInterface("axis_s_tdata", "i", word_size),
                ModuleInterface("axis_s_tlast", "i"),
            ),
        ]
        return self.generic_generate_module_header(interfaces)

    def _generate_module_foot(self) -> str:
        return f"\nendmodule // {self.design_name}\n"

    def _generate_accumulator_instance(self) -> str:
        template = self.acc_verilog.generic_generate_module_instance_template()
        return template.format(
            instance_name="",
            clk="aclk",
            rst_n="areset_n",
            acc_input="axis_s_tdata",
            acc_output="acc_output",
            feedback="(!feedback_control_reg & axis_s_tvalid)",
        )

    def _get_feedback_control_template(self):
        path = self.proj_path / "src/generators/templates/rs_axis.txt"
        with open(path, "r") as f:
            template = f.read()
        return template

    def _generate_feedback_control(self) -> str:
        template = self._get_feedback_control_template()
        return template.format(
            n_parity_max=self.acc_verilog.params["n_parity_sym"],
            word_size=self.acc_verilog.params["word_size"],
        )

    def _generate_module_body(self) -> str:
        return self._generate_feedback_control() + self._generate_accumulator_instance()

    def _generate_module(self, *args, **kwargs) -> str:
        return self._generate_module_header() + self._generate_module_body() + self._generate_module_foot()

    def generate_all_files(
        self,
        segment_path: Path | str | None = None,
        acc_filepath: Path | str | None = None,
        axis_filepath: Path | str | None = None,
    ):
        self.acc_verilog.generate_all_to_dir(segment_path, acc_filepath)
        self.generate_to_dir(axis_filepath)


if __name__ == "__main__":
    seg_params: RSSegmentVerilogParameters = {
        "gf_degree": 10,
        "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
        "constant_multplicants": [0],  # To populate in init
    }

    acc_params: RSAccumulatorVerilogParameters = {
        "word_size": 10,
        "n_parity_sym": 10,
        "segment_generator_params": seg_params,
    }

    params: RSAXISVerilogParameters = {
        "acc_params": acc_params,
    }

    RSAcc = RSAXISVerilogGenerator(params)

    RSAcc.generate_all_files()
