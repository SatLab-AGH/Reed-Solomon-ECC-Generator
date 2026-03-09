from __future__ import annotations

import logging
import os
import random
from pathlib import Path

import cocotb
import numpy as np
import pytest
import reedsolo as rs
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, with_timeout
from cocotb_tools.runner import get_runner
from cocotbext.axi import AxiStreamBus, AxiStreamFrame, AxiStreamSink, AxiStreamSource

from generators.logging_config import setup_logging
from generators.RSAXISVerilog import RSAXISVerilogGenerator, RSAXISVerilogParameters

logger = logging.getLogger("cocotb.rs_axis")

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


def check_data(tx_frame: AxiStreamFrame, rx_frame: AxiStreamFrame):
    assert tx_frame.tdata == rx_frame.tdata[: len(tx_frame.tdata)], (
        "Payload data mismatch\n",
        f"TX={tx_frame.tdata}\nRX={rx_frame.tdata[: len(tx_frame.tdata)]}",
    )
    ecc_len = int(cocotb.plusargs.get("ECC_LEN", "inf"))
    word_size = int(cocotb.plusargs.get("WORD_SIZE", "inf"))
    gf_prim = int(cocotb.plusargs.get("GF_PRIM", "inf"))
    rsc = rs.RSCodec(nsym=ecc_len, nsize=(1 << word_size) - 1, prim=gf_prim, c_exp=word_size)
    reference_ecc_frame = rsc.encode(tx_frame.tdata)
    assert len(reference_ecc_frame) == len(rx_frame.tdata)
    assert list(reference_ecc_frame) == rx_frame.tdata, (
        "Payload frame mismatch\n",
        f"TX={reference_ecc_frame}\nRX={rx_frame.tdata}",
    )


@cocotb.test()
async def RS_AXIS_random_streams(dut):
    word_size = int(cocotb.plusargs.get("WORD_SIZE", "inf"))
    # create buses
    dut_sbus = AxiStreamBus(dut, prefix="axis_s")
    dut_mbus = AxiStreamBus(dut, prefix="axis_m")

    cocotb.start_soon(Clock(dut.aclk, 2, unit="ns").start())
    await reset_dut(dut)

    # drivers
    axis_source = AxiStreamSource(dut_sbus, dut.aclk, dut.areset_n, reset_active_level=False)
    await RisingEdge(dut.aclk)
    axis_sink = AxiStreamSink(dut_mbus, dut.aclk, dut.areset_n, reset_active_level=False)

    await reset_dut(dut)

    # start randomized ready behavior
    cocotb.start_soon(random_backpressure(dut))

    for frame_idx in range(FRAME_COUNT):
        length = random.randint(1, MAX_FRAME_LEN)

        tx_payload = [random.randint(0, (1 << word_size) - 1) for _ in range(length)]

        tx_frame = AxiStreamFrame(tx_payload)  # pyright: ignore[reportArgumentType]

        dut._log.info(f"Sending frame {frame_idx}: {tx_payload}")

        await axis_source.send(tx_frame)

        rx_frame = await with_timeout(axis_sink.recv(), 200, "us")

        dut._log.info(f"Received frame {frame_idx}: {list(rx_frame.tdata)}")

        check_data(tx_frame, rx_frame)

    await Timer(100, "ns")


@pytest.mark.parametrize(
    "ecc_len",
    [(2**i) - 1 for i in range(1, 10)],
)
def test_runner(ecc_len):
    setup_logging(f"RS_AXIS/{ecc_len}.log")

    axis_params: RSAXISVerilogParameters = {
        "word_size": 10,
        "n_parity_sym": 10,
        "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
    }

    generator = RSAXISVerilogGenerator(axis_params) 

    rtl_axis_dir = f"RS_AXIS/{ecc_len}"
    rtl_acc_path = f"RS_AXIS/{ecc_len}"
    rtl_seg_path = f"RS_AXIS/{ecc_len}"

    generator.params["n_parity_sym"] = ecc_len
    generator.acc_verilog.set_generator_poly_len(ecc_len)
    generator.generate_all_files(rtl_seg_path, rtl_acc_path, rtl_axis_dir)

    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent.parent

    sources = [
        proj_path / "build/rtl" / rtl_axis_dir / "RS_AXIS.v",
        proj_path / "build/rtl" / rtl_acc_path / "RS_Accumulator.v",
        proj_path / "build/rtl" / rtl_seg_path / "RS_Segment.v",
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
        plusargs=[
            f"+ECC_LEN={ecc_len}",
            f"+WORD_SIZE={axis_params['word_size']!s}",
            f"+GF_PRIM={generator.acc_verilog.segment_generator.irreducible_poly._integer!s}",
        ],
    )
