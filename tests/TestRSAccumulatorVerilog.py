from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass
from pathlib import Path

import cocotb
import numpy as np
import pytest
import reedsolo as rs
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb_tools.runner import get_runner

from generators.logging_config import setup_logging
from generators.RSAccumulatorVerilog import RSAccumulatorVerilogGenerator, RSAccumulatorVerilogParameters

logger = logging.getLogger("cocotb.segment")

proj_path = Path(__file__).resolve().parent.parent

acc_params: RSAccumulatorVerilogParameters = {
    "word_size": 10,
    "n_parity_sym": 1,
    "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
    "constant_multplicants": [],
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
    ecc_len = int(cocotb.plusargs.get("ECC_LEN", "inf"))
    c_exp = 10  # 10-bit symbols → GF(2^10)

    try:
        rsc = rs.RSCodec(ecc_len, c_exp=c_exp, prim=gf_poly_coeffs, nsize=1023)
    except ValueError as e:
        raise ValueError(f"{e}: {ecc_len}<{len(rs_data_in) + rs_data_in.ecc_len}")
    logger.debug(f"Using rsc {rsc.gen}")
    encoded = rsc.encode(rs_data_in.data)
    computed_ecc = list(encoded[len(rs_data_in.data) :])
    dut_ecc = rs_data_out.ecc
    logger.debug(f"Exp msg: {encoded} \n DUT msg: {np.concat((rs_data_out.data, dut_ecc))} \n")
    assert np.array_equal(computed_ecc, rs_data_out.ecc), (
        f"ECC mismatch: computed {computed_ecc}, dut returned {dut_ecc}; using poly: {rsc.gen}"
    )


async def accumulator_driver(dut, rs_data_in: RSInputData):
    logger.info(
        f"Starting segment driver with data of length {len(rs_data_in)}and ECC length {{rs_data_in.ecc_len}}"
    )
    dut.rst_n.value = 1
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

    await Timer(5, "ns")

    return RSOutputData(data, ecc)


@cocotb.test()
async def RS_Accumulator_random(dut):
    logger.info("Starting DFF simple test...")

    ecc_len = int(cocotb.plusargs.get("ECC_LEN", "inf"))
    rs_data_in = RSInputData(
        np.array([random.randint(0, 1023) for _ in range(1022 - ecc_len)], dtype=int), ecc_len
    )

    clock = Clock(dut.clk, 1000)

    cocotb.start_soon(clock.start(start_high=False))

    driver = cocotb.start_soon(accumulator_driver(dut, rs_data_in))
    overseer = cocotb.start_soon(accumulator_overseer(dut, rs_data_in))

    await driver
    rs_data_out = await overseer

    validate_RS_ECC(rs_data_in, rs_data_out)


@pytest.mark.parametrize(
    "ecc_len",
    [(2**i) - 1 for i in range(1, 9)],
)
def test_runner(ecc_len):
    setup_logging(f"RS_Accumulator/{ecc_len}.log")
    rtl_acc_dir = f"RS_Accumulator/{ecc_len}"
    rtl_seg_dir = f"RS_Accumulator/{ecc_len}"

    _generator.set_generator_poly_len(ecc_len)
    _generator.generate_all_to_dir(rtl_seg_dir, rtl_acc_dir)
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent.parent

    sources = [
        proj_path / "build/rtl/" / rtl_acc_dir / "RS_Accumulator.v",
        proj_path / "build/rtl" / rtl_seg_dir / "RS_Segment.v",
    ]
    hdl_toplevel = "RS_Accumulator"

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel=hdl_toplevel,
        always=True,
        build_dir=proj_path / "build/cocotb" / hdl_toplevel / str(ecc_len),
    )

    runner.test(
        hdl_toplevel="RS_Accumulator",
        test_module="tests.TestRSAccumulatorVerilog",
        plusargs=[f"+ECC_LEN={ecc_len}", f"+GF_DEGREE ={acc_params['word_size']!s}"],
    )
