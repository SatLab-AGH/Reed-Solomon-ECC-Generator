from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

import cocotb
import numpy as np
import pytest
import reedsolo as rs
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb_tools.runner import get_runner

from generators.RSAccumulatorVerilog import RSAccumulatorVerilogGenerator, RSAccumulatorVerilogParameters
from generators.RSSegmentVerilog import RSSegmentVerilogParameters

logger = logging.getLogger("cocotb.segment")
logger.setLevel(logging.INFO)
proj_path = Path(__file__).resolve().parent.parent
handle = RotatingFileHandler(
    proj_path.joinpath("logs/accumulatorverilog.log"), maxBytes=5 * 1024 * 1024, backupCount=3
)
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
)
handle.setFormatter(formatter)
logger.addHandler(handle)


def hexlist(lst, width=2, prefix='', sep=' '):
    return sep.join(f"{prefix}{x:0{width}x}" for x in lst)


seg_params: RSSegmentVerilogParameters = {
    "design_name": "RS_Segment",
    "description": "",
    "gf_degree": 10,
    "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
    "output_path": Path("rtl"),
    "constant_multplicants": []
}

acc_params: RSAccumulatorVerilogParameters = {
    "design_name": "RS_Accumulator",
    "description": "",
    "output_path": Path("rtl"),
    "word_size": 10,
    "n_parity_sym": 50,
    "segment_generator_params": seg_params
}

_generator = RSAccumulatorVerilogGenerator(acc_params)


@dataclass()
class RSInputData:
    data: np.ndarray
    ecc_len: int

    def __len__(self):
        return len(self.data)


@dataclass
class RSOutputData:
    data: np.ndarray
    ecc: np.ndarray

    def __len__(self):
        return len(self.data) + len(self.ecc)
    

def validate_RS_ECC(rs_data_in: RSInputData, rs_data_out: RSOutputData):
    gf_poly_coeffs = _generator.segment_generator.irreducible_poly._integer
    ecc_len = rs_data_in.ecc_len          # number of parity symbols
    c_exp = 10                            # 10-bit symbols → GF(2^10)

    rsc = rs.RSCodec(ecc_len, c_exp=c_exp, prim=gf_poly_coeffs)
    logger.debug(f"Using rsc {rsc.gen}")
    encoded = rsc.encode(rs_data_in.data)
    computed_ecc = list(encoded[len(rs_data_in.data):])
    dut_ecc = rs_data_out.ecc
    logger.debug(f"Exp msg: {encoded} \n DUT msg: {np.concat((rs_data_out.data, dut_ecc))} \n")
    assert np.array_equal(computed_ecc, rs_data_out.ecc), \
        f"ECC mismatch: computed {computed_ecc}, dut returned {dut_ecc}; using poly: {rsc.gen}"


async def accumulator_driver(dut, rs_data_in: RSInputData):
    logger.info(f"Starting segment driver with data of length {len(rs_data_in)}"
                "and ECC length {rs_data_in.ecc_len}")

    for word in rs_data_in.data:
        dut.feedback.value = 1
        dut.acc_input.value = int(word)
        await RisingEdge(dut.clk)

    for _ in range(rs_data_in.ecc_len):
        dut.feedback.value = 0
        dut.acc_input.value = 0
        await RisingEdge(dut.clk)


async def accumulator_overseer(dut, rs_data_in: RSInputData) -> RSOutputData:
    data = np.ndarray(len(rs_data_in.data), dtype=int)
    ecc = np.ndarray(rs_data_in.ecc_len, dtype=int)

    for i, _ in enumerate(data):
        await RisingEdge(dut.clk)
        data[i] = int(dut.acc_input.value)

    for i, _ in enumerate(ecc):
        await RisingEdge(dut.clk)
        ecc[i] = int(dut.acc_output.value)

    await Timer(5, 'ns')

    return RSOutputData(data, ecc)


@pytest.fixture(scope="session", autouse=True)
def setup():
    _generator.generate()


@cocotb.test()
async def RS_Accumulator_random(dut):
    logger.info("Starting DFF simple test...")

    ecc_len = _generator.params["n_parity_sym"]
    rs_data_in = RSInputData(np.array([random.randint(0, 1023) for _ in range(ecc_len)], dtype=int), ecc_len)

    clock = Clock(dut.clk, 1000)
    
    cocotb.start_soon(clock.start(start_high=False))
    
    driver = cocotb.start_soon(accumulator_driver(dut, rs_data_in))
    overseer = cocotb.start_soon(accumulator_overseer(dut, rs_data_in))
    
    await driver
    rs_data_out = await overseer

    validate_RS_ECC(rs_data_in, rs_data_out)


# @pytest.mark.parametrize(
#     "ecc_len",
#     [i for i in range(20)],
# )
def test_runner():
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent.parent

    sources = [proj_path / "rtl/RS_Accumulator.v", ]
    sources = [proj_path / "rtl/RS_Accumulator.v", proj_path / "rtl/RS_Segment_Deg10.v"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="RS_Accumulator",
        always=True,
    )

    runner.test(
        hdl_toplevel="RS_Accumulator",
        test_module="tests.TestRSAccumulatorVerilog",
    )
