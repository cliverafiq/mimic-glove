"""
Drop-in replacement for simulator.glove_simulator.stream().

Usage:
    GLOVE_PORT=/dev/tty.usbserial-0001 python -m uvicorn server.app:app ...

Environment variables:
    GLOVE_PORT   Serial port path  (default: /dev/ttyUSB0)
    GLOVE_BAUD   Baud rate         (default: 115200)
"""

import asyncio
import os
import threading
import time

import serial

from hardware.protocol import MAGIC, PACKET_SIZE, decode


def _reader_thread(
    port: str,
    baud: int,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
    stop_event: threading.Event,
):
    start = time.monotonic()
    try:
        ser = serial.Serial(port, baud, timeout=2)
    except serial.SerialException as e:
        print(f"[serial_reader] could not open {port}: {e}", flush=True)
        return

    with ser:
        while not stop_event.is_set():
            try:
                # Scan for magic header
                byte = ser.read(1)
                if byte != b"\xaa":
                    continue
                byte = ser.read(1)
                if byte != b"\xbb":
                    continue

                # Read the remaining 11 bytes
                rest = ser.read(PACKET_SIZE - 2)
                if len(rest) != PACKET_SIZE - 2:
                    continue

                buf = MAGIC + rest
                channels = decode(buf)
                if channels is None:
                    continue

                packet = {
                    "timestamp": time.monotonic() - start,
                    "channels": channels,
                }
                asyncio.run_coroutine_threadsafe(queue.put(packet), loop)

            except serial.SerialException as e:
                print(f"[serial_reader] connection lost: {e}", flush=True)
                return

    print(f"[serial_reader] stop requested, closing {port}", flush=True)


async def stream(queue: asyncio.Queue):
    port = os.environ.get("GLOVE_PORT", "/dev/ttyUSB0")
    if "GLOVE_PORT" not in os.environ:
        print(
            f"[serial_reader] WARNING: GLOVE_PORT not set, defaulting to {port!r}. "
            "On macOS the ESP32 typically appears as /dev/tty.usbserial-XXXX — "
            "set GLOVE_PORT to the correct device.",
            flush=True,
        )

    baud = int(os.environ.get("GLOVE_BAUD", "115200"))
    loop = asyncio.get_running_loop()
    stop_event = threading.Event()

    t = threading.Thread(
        target=_reader_thread,
        args=(port, baud, queue, loop, stop_event),
        daemon=True,
    )
    t.start()

    # Keep the coroutine alive until cancelled
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        stop_event.set()   # signal thread to exit its read loop and close the port
        raise
