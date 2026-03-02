# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0
from __future__ import annotations

import logging
import os
import random
from pathlib import Path

import bitarray
import cocotb
import numpy as np
import pytest
from cocotb.triggers import Timer
from cocotb_tools.runner import get_runner

from generators.MastrovitoVerilog import MastrovitoVerilogGenerator, MastrovitoVerilogParameters
from generators.logging_config import setup_logging

logger = logging.getLogger(__name__)


constant_multiplicants = [random.randint(0, 1023) for _ in range(20)]
params: MastrovitoVerilogParameters = {
    "gf_degree": 10,
    "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
    "constant_multplicants": list(constant_multiplicants),
}
_generator = MastrovitoVerilogGenerator(params)


@cocotb.test()
async def dff_simple_test(dut):
    A = int(dut.GF_CONST_MULT.value)
    for _ in range(1000):
        dut.B.value = random.randint(0, 1023)
        dut.C.value = random.randint(0, 1023)
        await Timer(1, "ps")
        gen_field = _generator.gf_field
        A_g = gen_field(A)
        B_g = gen_field(int(dut.B.value))
        C_g = gen_field(int(dut.C.value))

        expected = gen_field(A_g * B_g + C_g)
        dut_value = gen_field(int(dut.PS.value))
        assert expected == dut_value, (
            f"For input A={A}, B={B_g}, C={C_g}; Expected {bitarray.bitarray(expected.tobytes())}, "
            + "got {bitarray.bitarray(dut_value.tobytes())}"
        )


@pytest.mark.parametrize(
    "A",
    constant_multiplicants,
)
def test_runner(A):
    setup_logging(f"GF_Mastrovito_Multiplier_Adder_Deg10/{A}.log")
    rtl_MMA_path = f"GF_Mastrovito_Multiplier_Adder_Deg10/{A}"
    _generator.generate_to_dir(rtl_MMA_path)

    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent.parent

    hdl_toplevel = "GF_Mastrovito_Multiplier_Adder_Deg10"
    sources = [proj_path / "build/rtl" / rtl_MMA_path / (hdl_toplevel + ".v")]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel=hdl_toplevel,
        parameters={"GF_CONST_MULT": A},
        always=True,
        build_dir=proj_path / "build/cocotb" / hdl_toplevel / str(A),
    )

    runner.test(
        hdl_toplevel="GF_Mastrovito_Multiplier_Adder_Deg10",
        test_module="tests.TestMastrovitoVerilog",
    )
