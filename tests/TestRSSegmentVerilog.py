from __future__ import annotations

import logging
import os
import random
from logging.handlers import RotatingFileHandler
from pathlib import Path

import cocotb
import numpy as np
import pytest
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb_tools.runner import get_runner

from generators.RSSegmentVerilog import RSSegmentVerilogGenerator, RSSegmentVerilogParameters

logger = logging.getLogger("cocotb.segment")
logger.setLevel(logging.DEBUG)
proj_path = Path(__file__).resolve().parent.parent
handle = RotatingFileHandler(
    proj_path.joinpath("logs/segmentverilog.log"), maxBytes=5 * 1024 * 1024, backupCount=3
)
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
)
handle.setFormatter(formatter)
logger.addHandler(handle)


constant_multiplicants = [random.randint(0, 1023) for _ in range(20)] + [1, 1023]
params: RSSegmentVerilogParameters = {
    "design_name": "RS_Segment",
    "description": "Zero Latency Galois Field 2^n multiplication "
        + "and addition module for custom Reed Solomon Encoding",
    "gf_degree": 10,
    "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
    "output_path": Path("rtl"),
    "constant_multplicants": list(constant_multiplicants)
}
_generator = RSSegmentVerilogGenerator(params)


async def segment_driver(dut, bi: list[int] | None = None, fi: list[int] | None = None, cycles=100):
    for i in range(cycles):
        await RisingEdge(dut.clk)
        dut.RS_Backward_I.value = random.randint(0, 1023) if bi is None else bi[i]
        dut.RS_Forward_I.value = random.randint(0, 1023) if fi is None else fi[i]


async def segment_overseer(dut, cycles=200):
    await Timer(10, "ps")
    A = int(dut.GF_CONST_MULT.value)
    gen_field = _generator.gf_field

    def MA_GF(A_g, B_g, C_g):
        return gen_field(A_g) * gen_field(B_g) + gen_field(C_g)
    
    await RisingEdge(dut.clk)
    for _ in range(cycles + 1):
        bi = dut.RS_Backward_I.value
        fi = dut.RS_Forward_I.value
        bo = dut.RS_Backward_O.value
        await RisingEdge(dut.clk)
        fo = dut.RS_Forward_O.value

        logger.info(f"bi: {bi}, fi: {fi}, bo: {bo}, fo: {fo}")

        expected = MA_GF(A, gen_field(int(bi)), gen_field(int(fi)))
        assert int(expected) == int(fo), f"Expected: {expected}, from dut got: {fo}, " \
                        f"using A: {A}, bi: {bi}, fi: {fi}, bo: {bo}, fo: {fo}"
        assert bi == bo, f"Expected: {bi}, from dut got: {bo}"


@pytest.fixture(scope="session", autouse=True)
def setup():
    _generator.generate_to_file()


@cocotb.test()
async def RS_Segment_Deg10_random(dut):
    logger.info("Starting DFF simple test...")
    clock = Clock(dut.clk, 1000)
    logger.info("Clock initialized")
    
    cocotb.start_soon(clock.start())
    logger.info("Clock started.")
    driver = cocotb.start_soon(segment_driver(dut))
    overseer = cocotb.start_soon(segment_overseer(dut))

    await driver
    await overseer


@cocotb.test()
async def RS_Segment_Deg10_edge(dut):
    logger.info("Starting DFF simple test...")
    clock = Clock(dut.clk, 1000)
    logger.info("Clock initialized")
    bi = [0, 1023, 0, 1023]
    fi = [0, 1023, 1023, 0]

    cocotb.start_soon(clock.start())
    logger.info("Clock started.")
    driver = cocotb.start_soon(segment_driver(dut, bi=bi, fi=fi, cycles=4))
    overseer = cocotb.start_soon(segment_overseer(dut))

    await driver
    await overseer


@pytest.mark.parametrize(
    "A",
    constant_multiplicants,
)
def test_runner(A):
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent.parent

    sources = [proj_path / "rtl/RS_Segment_Deg10.v"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="RS_Segment_Deg10",
        parameters={"GF_CONST_MULT": A},
        always=True,
    )

    runner.test(
        hdl_toplevel="RS_Segment_Deg10",
        test_module="tests.TestRSSegmentVerilog",
    )
