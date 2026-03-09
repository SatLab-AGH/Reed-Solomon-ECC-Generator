import argparse
import json
import os
import shutil
from pathlib import Path

import galois
import numpy as np

from generators.RSAXISVerilog import RSAXISVerilogGenerator, RSAXISVerilogParameters

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


def load_config(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Config file does not exist: {path}")

    if not path.is_file():
        raise ValueError(f"Config path is not a file: {path}")

    try:
        with Path.open(path, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")

    return config


def get_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--ECC_LEN", nargs="?", type=int, default=8)
    p.add_argument("--WORD_SIZE", nargs="?", type=int, default=8)
    p.add_argument("--IRR_GF_POLY", nargs="?", type=int, default=None)
    p.add_argument("--OUTPUT_DIR", nargs="?", type=Path, default=None)
    p.add_argument("--CONFIG", nargs="?", type=Path, default=None)
    args = p.parse_args()

    if args.CONFIG:
        config = load_config(args.CONFIG)
        args.COMPANY = str(config.get("company"))
        args.ENGINEER = str(config.get("engineer"))
        args.PROJECT_NAME = str(config.get("project_name"))
        args.IRR_GF_POLY = int(config["irr_gf_poly"])
        args.WORD_SIZE = int(config["word_size"])
        args.ECC_LEN = int(config["ecc_len"])
        args.OUTPUT_DIR = Path(config["outout_dir"])
    else:
        args.IRR_GF_POLY = (
            galois.irreducible_poly(2, args.WORD_SIZE)._integer
            if args.IRR_GF_POLY is None
            else args.IRR_GF_POLY
        )
        args.OUTPUT_DIR = (
            proj_path / "products" if args.OUTPUT_DIR is None else Path(args.OUTPUT_DIR).resolve()
        )

    return args


def main():
    args = get_args()
    Path(proj_path / "products/").mkdir(exist_ok=True, parents=True) if args.OUTPUT_DIR is None \
        else Path(args.OUTPUT_DIR).mkdir(exist_ok=True, parents=True)

    coeffs = integer_to_poly(args.IRR_GF_POLY, 2, args.WORD_SIZE)

    params: RSAXISVerilogParameters = {
        "company": args.COMPANY,
        "engineer": args.ENGINEER,
        "project_name": args.PROJECT_NAME,
        "irreducible_poly_coeffs": np.array(coeffs),
        "word_size": args.WORD_SIZE,
        "n_parity_sym": args.ECC_LEN,
    }

    RSAxis = RSAXISVerilogGenerator(params)

    RSAxis.generate_all_files("", "", "")
    print(RSAxis.filename)

    build_filepaths = [
        Path("build/rtl/RS_Segment.v"),
        Path("build/rtl/RS_AXIS.v"),
        Path("build/rtl/RS_Accumulator.v"),
    ]

    for filepath in build_filepaths:
        shutil.move(filepath, dst=args.OUTPUT_DIR / Path(filepath).name)


if __name__ == "__main__":
    main()
