import logging
import random

import galois
import pytest

from generators.Mastrovito import MastrovitoMatrixGenerator

logger = logging.getLogger(__name__)

TESTING_ITER = 1000


def generate_params(count):
    params = []
    for _ in range(count):
        degree = 10
        # Use the seeded rng instance
        a_const = random.randint(0, 2**degree-1)
        # Galois library uses the global numpy/random state, 
        # but we can specify the method
        poly = galois.irreducible_poly(2, degree, method="random")
        params.append((degree, a_const, poly))
    return params


pytestmark = pytest.mark.parametrize(
    "gf_degree, A_constant, g_poly", 
    generate_params(20)
)


def test_MastrovitoMatrixGenerator(gf_degree, A_constant, g_poly: galois.Poly):
    mastro = MastrovitoMatrixGenerator(gf_degree, g_poly.coeffs.tolist())
    gal_field = mastro.gf_field
    gf_max = 1 << gf_degree

    for _ in range(TESTING_ITER):
        B = random.randint(0, gf_max - 1)
        A_g = gal_field(A_constant)
        B_g = gal_field(B) 
        C_mod = A_g * B_g
        C_mastro_2 = mastro._mastrovito_mult(A_constant, B)
        value = 0
        for b in C_mastro_2.tobytes():
            value = (value << 1) | (b & 1)   # b & 1 ensures 0/1 even if b is boolean
        C_mastro = gal_field(value)

        err_msg = (
            f"Multiplication of {A_constant:0{mastro.gf_degree}b}*{B:0{mastro.gf_degree}b}"
            + f" mod {mastro.gf_field.irreducible_poly} \n"
            + f" using {mastro.get_mastrovito(A_constant)} produced {C_mastro_2}"
        )
        assert C_mastro == C_mod, err_msg

    logger.info(f"PASS | Parameters> gf_degree:{gf_degree}, A_constant:{A_constant}, g_poly:{g_poly}")