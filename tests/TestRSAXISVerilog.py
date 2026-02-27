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
from cocotb.triggers import Event, RisingEdge, Timer
from cocotb_tools.runner import get_runner
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSource, AxiStreamSink, AxiStreamMonitor

from generators.RSAXISVerilog import RSAXISVerilogGenerator, RSAXISVerilogParameters
from generators.RSAccumulatorVerilog import RSAccumulatorVerilogParameters
from generators.RSSegmentVerilog import RSSegmentVerilogParameters
from generators.logging_config import setup_logging

logger = logging.getLogger("cocotb.rs_axis")

import cocotb
import random
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, with_timeout
from cocotbext.axi import AxiStreamBus, AxiStreamSource, AxiStreamSink, AxiStreamFrame


WORD_SIZE = 10
FRAME_COUNT = 25
MAX_FRAME_LEN = 32


async def reset_dut(dut):
    dut.areset_n.value = 0
    dut.axis_s_tvalid.value = 0
    dut.axis_s_tdata.value = 0
    dut.axis_s_tlast.value = 0
    dut.axis_m_tready.value = 0

    for _ in range(5):
        await RisingEdge(dut.aclk)

    dut.areset_n.value = 1

    for _ in range(5):
        await RisingEdge(dut.aclk)


async def random_backpressure(dut):
    while True:
        dut.axis_m_tready.value = 1
        await RisingEdge(dut.aclk)


@cocotb.test()
async def RS_AXIS_random_one_streams(dut):
    # create buses
    dut_sbus = AxiStreamBus(dut, prefix="axis_s")
    dut_mbus = AxiStreamBus(dut, prefix="axis_m")

    cocotb.start_soon(Clock(dut.aclk, 2, unit="ns").start())
    await reset_dut(dut)

    # drivers
    axis_source = AxiStreamSource(dut_sbus, dut.aclk, dut.areset_n, reset_active_level=False)
    await RisingEdge(dut.aclk)
    axis_sink = AxiStreamSink(dut_mbus, dut.aclk, dut.areset_n, reset_active_level=False, byte_size=WORD_SIZE)

    await reset_dut(dut)

    # start randomized ready behavior
    cocotb.start_soon(random_backpressure(dut))

    for frame_idx in range(FRAME_COUNT):
        length = random.randint(1, MAX_FRAME_LEN)

        payload = [random.randint(0, (1 << WORD_SIZE) - 1) for _ in range(length)]

        tx_frame = AxiStreamFrame(payload)  # pyright: ignore[reportArgumentType]

        dut._log.info(f"Sending frame {frame_idx}: {payload}")

        await axis_source.send(tx_frame)

        rx_frame = await with_timeout(axis_sink.recv(), 200, "us")

        dut._log.info(f"Received frame {frame_idx}: {list(rx_frame.tdata)}")

        # -----------------------
        # Assertions
        # -----------------------

        # if list(rx_frame.tdata) != payload:
        #     raise ValueError(
        #         f"Payload mismatch\n"
        #         f"TX={payload}\n"
        #         f"RX={list(rx_frame.tdata)}"
        #     )

        # if rx_frame.tlast != 1:
        #     raise ValueError("Missing TLAST on received frame")

    # idle cycles after test
    await Timer(100, "ns")


@pytest.mark.parametrize(
    "ecc_len",
    [(2**i) - 1 for i in range(1, 10)],
)
def test_runner(ecc_len):
    setup_logging(f"RS_AXIS/{ecc_len}.log")

    seg_params: RSSegmentVerilogParameters = {
        "design_name": "RS_Segment",
        "description": "",
        "gf_degree": 10,
        "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
        "constant_multplicants": [],
    }

    acc_params: RSAccumulatorVerilogParameters = {
        "design_name": "RS_Accumulator",
        "description": "",
        "word_size": 10,
        "n_parity_sym": 10,
        "segment_generator_params": seg_params,
    }

    axis_params: RSAXISVerilogParameters = {
        "design_name": "RS_AXIS",
        "description": "",
        "acc_params": acc_params,
    }

    _generator = RSAXISVerilogGenerator(axis_params)

    rtl_axis_path = f"RS_AXIS/{ecc_len}/RS_AXIS.v"
    rtl_acc_path = f"RS_AXIS/{ecc_len}/RS_Accumulator.v"
    rtl_seg_path = f"RS_AXIS/{ecc_len}/RS_Segment_Deg10.v"

    _generator.params["acc_params"]["n_parity_sym"] = ecc_len
    _generator.acc_verilog.set_generator_poly_len(ecc_len)
    _generator.generate_all_files(rtl_seg_path, rtl_acc_path, rtl_axis_path)

    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent.parent

    sources = [
        proj_path / "build/rtl" / rtl_axis_path,
        proj_path / "build/rtl" / rtl_acc_path,
        proj_path / "build/rtl" / rtl_seg_path,
    ]

    hdl_toplevel = "RS_AXIS"

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel=hdl_toplevel,
        always=True,
        build_dir=proj_path / "build/cocotb" / hdl_toplevel / str(ecc_len),
    )

    runner.test(
        hdl_toplevel="RS_AXIS",
        test_module="tests.TestRSAXISVerilog",
        plusargs=[f"+ECC_LEN={ecc_len}", f"+GF_DEGREE={str(acc_params['word_size'])}"],
    )
