import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if os.environ.get("GLOVE_SOURCE") == "hardware":
    from hardware.serial_reader import stream
else:
    from simulator.glove_simulator import stream
from pipeline.parser import parse
from pipeline.servo_controller import compute_servo_state
from pipeline.gesture_recorder import GestureRecorder, playback_producer
from pipeline.calibration import Calibration
from pipeline.gesture_recognizer import GestureRecognizer

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

recorder = GestureRecorder()
calibration = Calibration()
recognizer = GestureRecognizer()
cmd_queue: asyncio.Queue = None
_latest_raw = [2048] * 5  # updated each frame; used by calibration capture


@asynccontextmanager
async def lifespan(app):
    global cmd_queue
    cmd_queue = asyncio.Queue()
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# ── Recording ────────────────────────────────────────────────────────────────

@app.post("/record/start/{name}")
async def record_start(name: str):
    recorder.start(name)
    await cmd_queue.put({"cmd": "record_start", "name": name})
    return {"status": "recording", "name": name}


@app.post("/record/stop")
async def record_stop():
    try:
        name = recorder.stop()
    except RuntimeError:
        return {"status": "error", "detail": "no active recording"}
    recognizer.reload()
    await cmd_queue.put({"cmd": "record_stop"})
    return {"status": "saved", "name": name}


@app.get("/gestures")
async def list_gestures():
    return {"gestures": recorder.list()}


@app.post("/playback/{name}")
async def start_playback(name: str):
    await cmd_queue.put({"cmd": "playback", "name": name})
    return {"status": "playback", "name": name}


# ── Gesture recognition ───────────────────────────────────────────────────────

@app.post("/recognizer/reload")
async def reload_recognizer():
    recognizer.reload()
    return {"status": "reloaded", "known_gestures": recognizer.known_gestures()}


# ── Calibration ───────────────────────────────────────────────────────────────

@app.get("/calibration")
async def get_calibration():
    return calibration.to_dict()


@app.post("/calibration/capture/flat")
async def capture_flat():
    calibration.capture_flat(_latest_raw)
    return {"status": "ok", "captured": _latest_raw, **calibration.to_dict()}


@app.post("/calibration/capture/fist")
async def capture_fist():
    calibration.capture_fist(_latest_raw)
    return {"status": "ok", "captured": _latest_raw, **calibration.to_dict()}


@app.post("/calibration/save")
async def save_calibration():
    calibration.save()
    return {"status": "saved", **calibration.to_dict()}


@app.post("/calibration/reset")
async def reset_calibration():
    calibration.reset()
    return {"status": "reset", **calibration.to_dict()}


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=20)
    producer = asyncio.create_task(stream(queue))
    mode = "simulate"

    try:
        while True:
            if cmd_queue is not None:
                try:
                    cmd = cmd_queue.get_nowait()
                    if cmd["cmd"] == "playback":
                        try:
                            frames = recorder.load(cmd["name"])
                        except FileNotFoundError:
                            frames = None
                        if frames:
                            producer.cancel()
                            producer = asyncio.create_task(playback_producer(frames, queue))
                            mode = "playback"
                    elif cmd["cmd"] == "record_start":
                        mode = "recording"
                    elif cmd["cmd"] == "record_stop":
                        mode = "simulate"
                except asyncio.QueueEmpty:
                    pass

            try:
                packet = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            if packet.get("_done"):
                producer = asyncio.create_task(stream(queue))
                mode = "simulate"
                continue

            if packet.get("_pre_parsed"):
                parsed = {"timestamp": packet["timestamp"], "angles": packet["angles"]}
            else:
                _latest_raw[:] = packet["channels"]
                parsed = parse(packet, calibration.values)

            if recorder.is_recording:
                recorder.capture(parsed)

            servo_state = compute_servo_state(parsed)
            gesture = recognizer.recognize(parsed["angles"])
            payload = {
                "timestamp": parsed["timestamp"],
                "angles": parsed["angles"],
                "servos": servo_state["servos"],
                "mode": mode,
                "gesture": gesture,
            }
            await websocket.send_text(json.dumps(payload))

    except WebSocketDisconnect:
        pass
    finally:
        producer.cancel()
