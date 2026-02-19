# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0
from __future__ import annotations

import logging
import os
import random
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb_tools.runner import get_runner
import pytest
import bitarray

from generators.MastrovitoVerilog import MastrovitoVerilogGenerator

logger = logging.getLogger(__name__)

_generator = MastrovitoVerilogGenerator()

@cocotb.test()
async def dff_simple_test(dut):
    A = int(dut.GF_CONST_MULT.value)
    for _ in range(1000):
        dut.B.value = random.randint(0, 1023)
        dut.C.value = 0*random.randint(0, 1023)
        await Timer(1, 'ps')
        gen_field = _generator.gf_field
        A_g = gen_field(A)
        B_g = gen_field(int(dut.B.value))
        C_g = gen_field(int(dut.C.value))

        expected = gen_field(A_g * B_g + C_g)
        dut_value = gen_field(int(dut.PS.value))
        assert expected == dut_value, f"For input A={A}, B={B_g}, C={C_g}; Expected {bitarray.bitarray(expected.tobytes())}, got {bitarray.bitarray(dut_value.tobytes())}"

@pytest.mark.parametrize(
        "A",[245, 999, 1, 2, 3, 512],
)
def test_runner(A):
    # _generator.print_verilog_file()

    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent.parent

    sources = [proj_path / "rtl/GF_Mastrovito_Multiplier_Adder_Deg10.v"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="GF_Mastrovito_Multiplier_Adder_Deg10",
        parameters={"GF_CONST_MULT":A},
        always=True,
    )

    runner.test(hdl_toplevel="GF_Mastrovito_Multiplier_Adder_Deg10", test_module="tests.TestMastrovitoVerilogGenerator")