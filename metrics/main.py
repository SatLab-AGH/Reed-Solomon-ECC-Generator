import argparse
from asyncio import Queue
import asyncio
from concurrent.futures import ProcessPoolExecutor
import logging
from pathlib import Path

import numpy as np
from RSDataGen import RSDataGen
from RSEval import RSEval
from RSApply import RSApply
from BERInject import BERInject
from Visualizer import BERCurve
from functools import partial

logger = logging.getLogger(__name__)


def run_ber_pipeline(BER, DATA_LEN, ECC_LEN, WORD_SIZE, MSG_QUANT, IRR_GF_POLY):
    """
    Run the asyncio pipeline for a single BER in a separate process.
    Returns: (BER, (input_ber_, output_ber_))
    """

    async def pipeline():
        # Queues are local to this process
        gen_q = asyncio.Queue(10)
        ref_q = asyncio.Queue(10)
        enc_q = asyncio.Queue(10)
        inj_enc_q = asyncio.Queue(10)

        rsdategen = RSDataGen(WORD_SIZE, DATA_LEN, MSG_QUANT)
        rsapply = RSApply(WORD_SIZE, ECC_LEN, IRR_GF_POLY)
        berinject = BERInject(WORD_SIZE, BER)
        rseval = RSEval(WORD_SIZE, ECC_LEN, IRR_GF_POLY)

        async with asyncio.TaskGroup() as tg:
            tg.create_task(rsdategen.run(gen_q, ref_q))
            tg.create_task(rsapply.run(gen_q, enc_q))
            tg.create_task(berinject.run(enc_q, inj_enc_q))
            rseval_task = tg.create_task(rseval.run(inj_enc_q, ref_q))

        return BER, rseval_task.result()

    return asyncio.run(pipeline())


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--DATA_LEN", nargs="?", type=int, default=64)
    p.add_argument("--ECC_LEN", nargs="?", type=int, default=64)
    p.add_argument("--WORD_SIZE", nargs="?", type=int, default=8)
    p.add_argument("--MSG_QUANT", nargs="?", type=int, default=100)
    p.add_argument("--IRR_GF_POLY", nargs="?", type=int, default=None)
    p.add_argument("--BER", nargs="?", type=float, default=None)
    p.add_argument("--BER_MIN", nargs="?", type=float, default=None)
    p.add_argument("--BER_MAX", nargs="?", type=float, default=None)
    p.add_argument("--BER_STEPS", nargs="?", type=int, default=10)
    p.add_argument("--LOG_LVL", nargs="?", type=int, default=logging.INFO)
    p.add_argument("--DEBUG", action="store_true", help="Run sequentially for easier debugging")
    args = p.parse_args()

    if args.DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(args.LOG_LVL)

    DATA_LEN = int(args.DATA_LEN)
    ECC_LEN = int(args.ECC_LEN)
    WORD_SIZE = int(args.WORD_SIZE)
    MSG_QUANT = int(args.MSG_QUANT)
    IRR_GF_POLY = int(args.IRR_GF_POLY) if args.IRR_GF_POLY else 0x11

    input_ber_lst = []
    output_ber_lst = []

    if args.BER:
        BER_VEC = [float(args.BER)]
    elif args.BER_MIN and args.BER_MAX and args.BER_STEPS:
        BER_EXP = (args.BER_MAX / args.BER_MIN) ** (1 / (args.BER_STEPS - 1))
        BER_VEC = (args.BER_MIN * BER_EXP ** np.arange(args.BER_STEPS)).tolist()
    else:
        raise ValueError(
            "BER_VEC must be specified either by singular BER or BER_MIN and BER_MAX and BER_STEP"
        )

    # --- Parallel execution using threads ---
    run_partial = partial(
        run_ber_pipeline,
        DATA_LEN=DATA_LEN,
        ECC_LEN=ECC_LEN,
        WORD_SIZE=WORD_SIZE,
        MSG_QUANT=MSG_QUANT,
        IRR_GF_POLY=IRR_GF_POLY,
    )

    with ProcessPoolExecutor() as executor:
        # Submit all BER simulations
        futures = [executor.submit(run_partial, BER) for BER in BER_VEC]

        # Collect results
        for future in futures:
            BER, (input_ber_, output_ber_) = future.result()
            input_ber_lst.append(input_ber_)
            output_ber_lst.append(output_ber_)
            logger.info(f"Simulated BER={BER} : IN {input_ber_} -> OUT {output_ber_}")

    ber_curve = BERCurve(
        data_len=DATA_LEN,
        ecc_len=ECC_LEN,
        word_size=WORD_SIZE,
        ber_min=BER_VEC[-1],
        ber_max=BER_VEC[0],
        input_ber_lst=input_ber_lst,
        output_ber_lst=output_ber_lst,
    )

    BERCurve.append_ber_json(Path(__file__).parent / "ber_curve.json", [ber_curve])


if __name__ == "__main__":
    asyncio.run(main())
