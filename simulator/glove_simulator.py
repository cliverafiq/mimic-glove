import asyncio
import math
import random
import time

FINGER_NAMES = ["thumb", "index", "middle", "ring", "pinky"]
ADC_MIN = 0
ADC_MAX = 4095
SAMPLE_RATE_HZ = 50


def _natural_wave(t: float, finger_index: int) -> float:
    phase = finger_index * 0.4
    base = math.sin(t * 0.8 + phase)
    noise = random.gauss(0, 0.02)
    return max(-1.0, min(1.0, base + noise))


def generate_packet(t: float) -> dict:
    channels = []
    for i in range(5):
        normalized = (_natural_wave(t, i) + 1.0) / 2.0
        adc = int(normalized * ADC_MAX)
        channels.append(adc)
    return {"timestamp": t, "channels": channels}


async def stream(queue: asyncio.Queue):
    interval = 1.0 / SAMPLE_RATE_HZ
    start = time.monotonic()
    while True:
        t = time.monotonic() - start
        packet = generate_packet(t)
        await queue.put(packet)
        await asyncio.sleep(interval)
