import argparse
import os
from pathlib import Path
import galois
import numpy as np

from generators.RSAXISVerilog import RSAXISVerilogGenerator, RSAXISVerilogParameters
from generators.RSAccumulatorVerilog import RSAccumulatorVerilogParameters
from generators.RSSegmentVerilog import RSSegmentVerilogParameters

proj_path = Path(__file__).parent.parent


def get_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--ECC_LEN", nargs="?", type=int, default=64)
    p.add_argument("--WORD_SIZE", nargs="?", type=int, default=8)
    p.add_argument("--IRR_GF_POLY", nargs="?", type=int, default=None)
    p.add_argument("--OUTPUT_DIR", nargs="?", type=int, default=None)
    args = p.parse_args()

    args.IRR_GF_POLY = (
        galois.irreducible_poly(2, args.WORD_SIZE) if args.IRR_GF_POLY is None else args.IRR_GF_POLY
    )
    args.OUTPUT_DIR = proj_path / "products" if args.OUTPUT_DIR is None else Path(args.OUTPUT_DIR)

    return args


def main():
    args = get_args()
    os.makedirs(proj_path / "products") if args.OUTPUT_DIR is None else os.makedirs(args.OUTPUT_DIR)

    seg_params: RSSegmentVerilogParameters = {
        "design_name": "RS_Segment",
        "gf_degree": 10,
        "irreducible_poly_coeffs": np.array([1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1]),
        "constant_multplicants": [0],  # To populate in init
    }

    acc_params: RSAccumulatorVerilogParameters = {
        "design_name": "RS_Accumulator",
        "word_size": 10,
        "n_parity_sym": 10,
        "segment_generator_params": seg_params,
    }

    params: RSAXISVerilogParameters = {
        "design_name": "RS_AXIS",
        "acc_params": acc_params,
    }

    RSAxis = RSAXISVerilogGenerator(params)

    RSAxis.generate_all_files("a", "b", "c")


if __name__ == "__main__":
    main()
