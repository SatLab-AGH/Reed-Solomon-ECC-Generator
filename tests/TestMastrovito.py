import logging
from logging.handlers import RotatingFileHandler
import random

import galois
import numpy as np
import pytest

from generators.Mastrovito import MastrovitoMatrixGenerator

loger = logging.getLogger(__name__)
loger.setLevel(logging.DEBUG)
handle = RotatingFileHandler("./logs/mastrovito.log", maxBytes=5 * 1024 * 1024, backupCount=3)
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s'
)
handle.setFormatter(formatter)
loger.addHandler(handle)

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

def test_MastrovitoMatrixGenerator(gf_degree, A_constant, g_poly:galois.Poly):
    mastro = MastrovitoMatrixGenerator(gf_degree, g_poly.coeffs.tolist())
    gf_max = 1 << gf_degree

    for _ in range(TESTING_ITER):
        B = random.randint(0, gf_max-1)
        (C_mod, C_mastro) = mastro._crosscheck_with_modulo(A_constant, B)

        err_msg = f"Multiplication of {A_constant:0{mastro.gf_degree}b}*{B:0{mastro.gf_degree}b} mod {mastro.gf_field.irreducible_poly} \n \
        using {mastro.get_mastrovito(A_constant)}"
        np.testing.assert_array_equal(C_mastro, C_mod, err_msg=err_msg)

    loger.info(f"PASS | Parameters> gf_degree:{gf_degree}, A_constant:{A_constant}, g_poly:{g_poly}")