import asyncio
import reedsolo as rs


class RSApply:
    def __init__(self, word_size: int, ecc_len: int, irr_gf_poly: int) -> None:
        self.word_size = word_size
        self.max_word_val = (1 << word_size) - 1
        self.ecc_len = ecc_len
        self.rsc = rs.RSCodec(self.ecc_len, c_exp=self.word_size, nsize=self.max_word_val)  # , ,

    async def run(self, in_q: asyncio.Queue, out_q: asyncio.Queue):
        while True:
            frame = await in_q.get()

            if frame is None:
                break

            await out_q.put(self.rsc.encode(frame))

        await out_q.put(None)  # shutdown signal
