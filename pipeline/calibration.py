import json
from pathlib import Path

CALIBRATION_FILE = Path(__file__).parent.parent / "calibration.json"
FINGER_NAMES = ["thumb", "index", "middle", "ring", "pinky"]
DEFAULTS = [(200, 3800)] * 5


class Calibration:
    def __init__(self):
        self._data = list(DEFAULTS)
        if CALIBRATION_FILE.exists():
            self._load()

    @property
    def values(self) -> list:
        return list(self._data)

    def capture_flat(self, raw_channels: list):
        for i, raw in enumerate(raw_channels[:5]):
            self._data[i] = (raw, self._data[i][1])

    def capture_fist(self, raw_channels: list):
        for i, raw in enumerate(raw_channels[:5]):
            self._data[i] = (self._data[i][0], raw)

    def save(self):
        payload = {"fingers": [
            {"name": FINGER_NAMES[i], "flat": flat, "fist": fist}
            for i, (flat, fist) in enumerate(self._data)
        ]}
        CALIBRATION_FILE.write_text(json.dumps(payload, indent=2))

    def reset(self):
        self._data = list(DEFAULTS)
        if CALIBRATION_FILE.exists():
            CALIBRATION_FILE.unlink()

    def to_dict(self) -> dict:
        return {"fingers": [
            {"name": FINGER_NAMES[i], "flat": flat, "fist": fist}
            for i, (flat, fist) in enumerate(self._data)
        ]}

    def _load(self):
        try:
            payload = json.loads(CALIBRATION_FILE.read_text())
            loaded = [(f["flat"], f["fist"]) for f in payload["fingers"]]
            if len(loaded) != 5:
                raise ValueError("expected 5 finger entries")
            self._data = loaded
        except (KeyError, ValueError, json.JSONDecodeError):
            self._data = list(DEFAULTS)
