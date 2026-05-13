import asyncio
import json
from pathlib import Path

GESTURES_DIR = Path(__file__).parent.parent / "gestures"


class GestureRecorder:
    def __init__(self):
        GESTURES_DIR.mkdir(exist_ok=True)
        self._recording = False
        self._name = None
        self._frames = []

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self, name: str):
        self._recording = True
        self._name = name
        self._frames = []

    def capture(self, parsed: dict):
        if self._recording:
            self._frames.append({
                "timestamp": parsed["timestamp"],
                "angles": parsed["angles"],
            })

    def stop(self) -> str:
        if not self._recording:
            raise RuntimeError("stop() called without an active recording")
        self._recording = False
        name = self._name
        path = GESTURES_DIR / f"{name}.json"
        path.write_text(json.dumps({
            "name": name,
            "frame_count": len(self._frames),
            "frames": self._frames,
        }, indent=2))
        self._name = None
        self._frames = []
        return name

    def list(self) -> list:
        return sorted(p.stem for p in GESTURES_DIR.glob("*.json"))

    def load(self, name: str) -> list:
        path = GESTURES_DIR / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(name)
        return json.loads(path.read_text())["frames"]


async def playback_producer(frames: list, queue: asyncio.Queue):
    for i, frame in enumerate(frames):
        if i > 0:
            gap = frame["timestamp"] - frames[i - 1]["timestamp"]
            await asyncio.sleep(max(0.0, gap))
        await queue.put({"_pre_parsed": True, "timestamp": frame["timestamp"], "angles": frame["angles"]})
    await queue.put({"_done": True})
