from asyncio import Queue
import asyncio
import random
from typing import Sequence


class BERInject:
    def __init__(self, word_size: int, error_rate: float) -> None:
        self.word_size = word_size
        self.max_word_val = (1 << word_size) - 1
        self.ber = error_rate

    async def run(self, in_q: asyncio.Queue, out_q: asyncio.Queue):
        while True:
            frame = await in_q.get()

            if frame is None:
                break

            await out_q.put(self.inject(frame))

        await out_q.put(None)  # shutdown signal

    def inject(self, frame: Sequence[int]) -> Sequence[int]:
        for i in range(len(frame)):
            if random.random() < self.ber:
                frame[i] ^= 1 << random.randint(0, self.word_size - 1)
        return frame
