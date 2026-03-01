import asyncio
import random
from typing import Sequence, Dict, Any


class RSDataGen:
    def __init__(self, word_size: int, data_len: int, msg_quantity: int = 1) -> None:
        self.word_size = word_size
        self.data_len = data_len
        self.max_word_val = (1 << word_size) - 1
        self.msg_quantity = msg_quantity

    def _generate(self) -> Sequence[Sequence[int]]:
        return [
            [random.randint(0, self.max_word_val) for _ in range(self.data_len)]
            for _ in range(self.msg_quantity)
        ]

    async def run(self, out_q: asyncio.Queue, ref_q: asyncio.Queue):
        frames = self._generate()
        for frame in frames:
            await out_q.put(frame)
            await ref_q.put(frame)

        await out_q.put(None)  # shutdown signal
        await ref_q.put(None)  # shutdown signal
