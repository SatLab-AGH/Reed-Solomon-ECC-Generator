import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Required, TypedDict

import galois
import numpy as np
from numpy.typing import ArrayLike, NDArray

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
proj_path = Path(__file__).resolve().parent.parent
handle = RotatingFileHandler(
    proj_path.joinpath("logs/mastrovito.log"), maxBytes=5 * 1024 * 1024, backupCount=3
)
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
)
handle.setFormatter(formatter)
logger.addHandler(handle)


class MastrovitoMatrixParameters(TypedDict):
    gf_degree: Required[int]
    irreducible_poly_coeffs: Required[np.ndarray]


class MastrovitoMatrixGenerator:
    """
    Calculates Mastrovito matrix to perform GF multiplication using only parralel XOR gates
    https://www.iiis.org/cds2010/cd2010imc/ccct_2010/paperspdf/ta999ne.pdf
    https://cetinkayakoc.net/docs/c18.pdf.
    """

    def __init__(self, params: MastrovitoMatrixParameters) -> None:

        self.gf_degree = params["gf_degree"]
        self.gf2_field = galois.GF(2, 1)
        self.irreducible_poly = galois.Poly(params["irreducible_poly_coeffs"], self.gf2_field)
        self.gf_field = galois.GF(2, self.gf_degree, irreducible_poly=self.irreducible_poly)

        self.mastrovito_matrix = None

    @staticmethod
    def num2bit(num, bitlen):
        return np.array([(int(digit)) for digit in f"{int(num):0{bitlen}b}"])

    @staticmethod
    def bit2num(bool_array):
        return int("".join(bool_array.astype(int).astype(str)), 2)

    def _calculate_reduction_matrix(self) -> np.ndarray:

        reduction_matrix = np.zeros((self.gf_degree), dtype=self.gf2_field)

        P_ext = self.gf_field.irreducible_poly

        for i in range(self.gf_degree, 2 * self.gf_degree):
            x_coeffs = np.zeros(2 * self.gf_degree)
            x_coeffs[-i - 1] = 1
            x_power_poly = galois.Poly(x_coeffs, self.gf2_field)
            reduced_power = x_power_poly % P_ext
            reduction_matrix[i - self.gf_degree] = galois.Poly(
                reduced_power.coeffs, self.gf2_field
            )

        return reduction_matrix

    def _calculate_mastrovito_matrix(self, A: int, reduction_matrix: NDArray) -> NDArray:

        mastrovito_matrix: NDArray = galois.GF2.Zeros((self.gf_degree, self.gf_degree))

        for i in range(self.gf_degree):
            A_ext = int(A) << i
            T_i = galois.Poly.Int(A_ext, self.gf2_field)

            for j in range(self.gf_degree, 2 * self.gf_degree):
                if int(T_i) & (1 << j):
                    T_i += galois.Poly.Int((1 << j), self.gf2_field)
                    T_i += reduction_matrix[j - self.gf_degree]

            T_i_coeff: np.ndarray = np.concatenate(
                [np.ndarray(self.gf_degree - len(T_i.coeffs)), T_i.coeffs]
            )

            mastrovito_matrix[i] = T_i_coeff

        return np.rot90(mastrovito_matrix)

    def get_mastrovito(self, A: int) -> NDArray:

        reduction_matrix = self._calculate_reduction_matrix()

        return self._calculate_mastrovito_matrix(A, reduction_matrix)

    def _mastrovito_mult(self, A: int, B: int | ArrayLike) -> np.ndarray:
        mastrovito_matrix = self.get_mastrovito(A)

        B_gf2 = np.flip(self.gf2_field(self.num2bit(B, self.gf_degree))).T

        C_mastro = self.gf2_field(mastrovito_matrix) @ B_gf2

        return C_mastro[::-1]
