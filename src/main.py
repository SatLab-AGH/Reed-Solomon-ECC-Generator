import argparse
import os
from pathlib import Path
import galois
import numpy as np

from generators.RSAXISVerilog import RSAXISVerilogGenerator, RSAXISVerilogParameters
from generators.RSAccumulatorVerilog import RSAccumulatorVerilogParameters
from generators.RSSegmentVerilog import RSSegmentVerilogParameters

proj_path = Path(__file__).parent.parent


def integer_to_poly(integer: int, order: int, degree: int | None = None) -> list[int]:
    """
    Converts the integer representation of the polynomial to its coefficients in descending order.
    """
    if order == 2:
        c = [int(bit) for bit in bin(integer)[2:]]
    else:
        c = []  # Coefficients in ascending order
        while integer > 0:
            q, r = divmod(integer, order)
            c.append(r)
            integer = q

        # Ensure the coefficient list is not empty
        if not c:
            c = [0]

        c = c[::-1]  # Coefficients in descending order

    # Set to a fixed degree if requested
    if degree is not None:
        assert degree >= len(c) - 1
        c = [0] * (degree - len(c) + 1) + c

    return c


def get_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--ECC_LEN", nargs="?", type=int, default=8)
    p.add_argument("--WORD_SIZE", nargs="?", type=int, default=8)
    p.add_argument("--IRR_GF_POLY", nargs="?", type=int, default=None)
    p.add_argument("--OUTPUT_DIR", nargs="?", type=Path, default=None)
    args = p.parse_args()

    args.IRR_GF_POLY = (
        galois.irreducible_poly(2, args.WORD_SIZE)._integer if args.IRR_GF_POLY is None else args.IRR_GF_POLY
    )
    args.OUTPUT_DIR = proj_path / "products" if args.OUTPUT_DIR is None else Path(args.OUTPUT_DIR)

    return args


def main():
    args = get_args()
    os.makedirs(proj_path / "products/", exist_ok=True) if args.OUTPUT_DIR is None else os.makedirs(
        args.OUTPUT_DIR, exist_ok=True
    )

    coeffs = integer_to_poly(args.IRR_GF_POLY, 2, args.WORD_SIZE)
    seg_params: RSSegmentVerilogParameters = {
        "gf_degree": args.WORD_SIZE,
        "irreducible_poly_coeffs": np.array(coeffs),
    }

    acc_params: RSAccumulatorVerilogParameters = {
        "word_size": args.WORD_SIZE,
        "n_parity_sym": args.ECC_LEN,
        "segment_generator_params": seg_params,
    }

    params: RSAXISVerilogParameters = {
        "acc_params": acc_params,
    }

    RSAxis = RSAXISVerilogGenerator(params)

    RSAxis.generate_all_files("", "", "")
    print(RSAxis.filename)
    # os.rename()


if __name__ == "__main__":
    main()
