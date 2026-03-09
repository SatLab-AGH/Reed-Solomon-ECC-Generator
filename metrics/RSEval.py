import asyncio
import random
from typing import Sequence, Dict, Any
import numpy as np
import reedsolo as rs


class RSEval:
    def __init__(self, word_size: int, ecc_len: int, irr_gf_poly: int) -> None:
        self.word_size = word_size
        self.max_word_val = (1 << word_size) - 1
        self.ecc_len = ecc_len
        self.rsc = rs.RSCodec(self.ecc_len, c_exp=self.word_size, nsize=self.max_word_val)

        self.word_count = 0
        self.in_ber_count = 0
        self.out_ber_count = 0

    def digest(self, frame: Sequence[int], ref_frame: Sequence[int]):
        try:
            dec_frame, _, _ = self.rsc.decode(frame)
        except:
            dec_frame = frame[: -self.ecc_len]

        for word, dec_word, ref_word in zip(frame, dec_frame, ref_frame):
            if word != ref_word:
                self.in_ber_count += 1
            if dec_word != ref_word:
                self.out_ber_count += 1

        self.word_count += len(ref_frame)

    def finish(self):
        # print(f"Error decoded words / words total: \t{self.in_ber_count}/\t{self.word_count} \
        #       => {self.in_ber_count / self.word_count * 100:.2f}%")
        # print(f"Corrected error decoded words / words total: \t{self.out_ber_count}/\t{self.word_count} \
        #       => {self.out_ber_count / self.word_count * 100:.2f}%")
        return (self.in_ber_count / self.word_count, self.out_ber_count / self.word_count)

    async def run(self, in_q: asyncio.Queue, ref_q: asyncio.Queue):
        while True:
            frame = await in_q.get()
            ref_frame = await ref_q.get()

            if frame is None or ref_frame is None:
                break

            self.digest(frame, ref_frame)

        return self.finish()
