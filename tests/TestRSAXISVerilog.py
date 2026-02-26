from __future__ import annotations

from enum import Enum
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

from generators.RSAXISVerilog import RSAXISVerilogGenerator, RSAXISVerilogParameters
from generators.RSAccumulatorVerilog import RSAccumulatorVerilogParameters
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


def hexlist(lst, width=2, prefix="", sep=" "):
    return sep.join(f"{prefix}{x:0{width}x}" for x in lst)


seg_params: RSSegmentVerilogParameters = {
    "design_name": "RS_Segment",
    "description": "",
    "gf_degree": 10,
    "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
    "output_path": Path("rtl"),
    "constant_multplicants": [],
}

acc_params: RSAccumulatorVerilogParameters = {
    "design_name": "RS_Accumulator",
    "description": "",
    "output_path": Path("rtl"),
    "word_size": 10,
    "n_parity_sym": 10,
    "segment_generator_params": seg_params,
}

axis_params: RSAXISVerilogParameters = {
    "design_name": "RS_AXIS",
    "description": "",
    "output_path": Path("rtl"),
    "acc_params": acc_params,
}

_generator = RSAXISVerilogGenerator(axis_params)


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


class RS_AXIS_Driver:
    def __init__(self, dut) -> None:
        self.dut = dut
        self.data_width = _generator.acc_verilog.params["word_size"]
        self.dut.TVALID_s.value = 0
        self.dut.TDATA_s.value = 0
        self.dut.TLAST_s.value = 0
        self.dut.TREADY_m.value = 0
        self.dut.ARESETn.value = 1

    async def simulate_receiving(self):
        self.dut.TREADY_m.value = 1

    async def send_one_word(self, word: int, max_wait_cycles=1024):
        for _ in range(max_wait_cycles):
            await RisingEdge(self.dut.ACLK)
            if self.dut.TREADY_s.value == 1:
                self.dut.TVALID_s.value = 1
                self.dut.TDATA_s.value = word
                self.dut.TLAST_s.value = 1
                await RisingEdge(self.dut.ACLK)
                self.dut.TVALID_s.value = 0
                self.dut.TLAST_s.value = 0
                return

        raise TimeoutError(f"RS_AXIS_Driver: send_data timed out cycles:{max_wait_cycles}")

    async def send_word_stream(self, word_stream: np.ndarray, max_wait_cycles=1024):
        for _ in range(max_wait_cycles):
            await RisingEdge(self.dut.ACLK)
            if self.dut.TREADY_s.value == 1:
                self.dut.TVALID_s.value = 1
                for idx, word in enumerate(word_stream):
                    if idx == len(word_stream) - 1:
                        self.dut.TLAST_s.value = 1
                    self.dut.TDATA_s.value = int(word)
                    await RisingEdge(self.dut.ACLK)
                    assert self.dut.TREADY_s.value == 1, "Stream must be continous"
                self.dut.TVALID_s.value = 0
                self.dut.TLAST_s.value = 0
                self.dut.TDATA_s.value = 0
                return

        raise TimeoutError(f"RS_AXIS_Driver: send_data timed out cycles:{max_wait_cycles}")


class RS_AXIS_Overseer:
    def __init__(self, dut) -> None:
        self.dut = dut
        self.data_width = _generator.acc_verilog.params["word_size"]

    async def record_word_stream(self, num_data: int, num_ecc: int, max_wait_cycles=1024):
        data_stream = np.ndarray((num_data), dtype=int)
        ecc_stream = np.ndarray((num_ecc), dtype=int)

        for _ in range(max_wait_cycles):
            await RisingEdge(self.dut.ACLK)
            if self.dut.TVALID_m.value == 1:
                for idx, word in enumerate(data_stream):
                    data_stream[idx] = int(self.dut.TDATA_m.value)
                    await RisingEdge(self.dut.ACLK)
                    assert self.dut.TVALID_m.value == 1, "Stream must be continous"
                for idx, word in enumerate(ecc_stream):
                    ecc_stream[idx] = int(self.dut.TDATA_m.value)
                    await RisingEdge(self.dut.ACLK)
                    # assert self.dut.TVALID_m.value == 1, "Stream must be continous"
                return RSOutputData(data_stream, ecc_stream)

        raise TimeoutError(f"RS_AXIS_Overseer: send_data timed out cycles:{max_wait_cycles}")


def validate_RS_ECC(rs_data_in: RSInputData, rs_data_out: RSOutputData):
    gf_poly_coeffs = _generator.acc_verilog.segment_generator.irreducible_poly._integer
    ecc_len = rs_data_in.ecc_len  # number of parity symbols
    c_exp = 10  # 10-bit symbols → GF(2^10)

    rsc = rs.RSCodec(ecc_len, c_exp=c_exp, prim=gf_poly_coeffs)
    logger.debug(f"Using rsc {rsc.gen}")
    encoded = rsc.encode(rs_data_in.data)
    computed_ecc = list(encoded[len(rs_data_in.data) :])
    dut_ecc = rs_data_out.ecc
    logger.debug(f"Exp msg: {encoded} \n DUT msg: {np.concat((rs_data_out.data, dut_ecc))} \n")
    assert len(computed_ecc) == len(rs_data_out.ecc)
    assert np.array_equal(computed_ecc, rs_data_out.ecc), (
        f"ECC mismatch: computed {computed_ecc}, dut returned {dut_ecc}; using poly: {rsc.gen}"
    )


@pytest.fixture(scope="session", autouse=True)
def setup():
    _generator.generate()


@cocotb.test()
async def RS_AXIS_random_two_streams(dut):
    logger.info("Starting DFF simple test...")

    rs_axis_driver = RS_AXIS_Driver(dut)
    rs_axis_overseer = RS_AXIS_Overseer(dut)

    ecc_len = _generator.acc_verilog.params["n_parity_sym"]
    rs_data_in = RSInputData(
        np.array([random.randint(0, 1023) for _ in range(random.randint(0, 100))], dtype=int), ecc_len
    )

    clock = Clock(dut.ACLK, 1000)
    await rs_axis_driver.simulate_receiving()
    cocotb.start_soon(clock.start(start_high=False))

    driver_task = cocotb.start_soon(rs_axis_driver.send_word_stream(rs_data_in.data))
    overseer_task = cocotb.start_soon(rs_axis_overseer.record_word_stream(len(rs_data_in), ecc_len))

    await driver_task
    rs_data_out = await overseer_task

    validate_RS_ECC(rs_data_in, rs_data_out)

    rs_data_in = RSInputData(
        np.array([random.randint(0, 1023) for _ in range(random.randint(0, 100))], dtype=int), ecc_len
    )

    driver_task_2 = cocotb.start_soon(rs_axis_driver.send_word_stream(rs_data_in.data))
    overseer_task_2 = cocotb.start_soon(rs_axis_overseer.record_word_stream(len(rs_data_in), ecc_len))

    await driver_task_2
    rs_data_out = await overseer_task_2

    validate_RS_ECC(rs_data_in, rs_data_out)

    await Timer(20, unit="ns")


# @pytest.mark.parametrize(
#     "ecc_len",
#     [i for i in range(20)],
# )
def test_runner():
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent.parent

    sources = [
        proj_path / "rtl/RS_AXIS.v",
        proj_path / "rtl/RS_Accumulator.v",
        proj_path / "rtl/RS_Segment_Deg10.v",
    ]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="RS_AXIS",
        always=True,
    )

    runner.test(
        hdl_toplevel="RS_AXIS",
        test_module="tests.TestRSAXISVerilog",
    )
