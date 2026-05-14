import json
import math
from pathlib import Path

GESTURES_DIR = Path(__file__).parent.parent / "gestures"

# Rule-based poses: (min°, max°) per finger [thumb, index, middle, ring, pinky]
BUILTIN_POSES = {
    "open":      [(0, 35),  (0, 35),  (0, 35),  (0, 35),  (0, 35) ],
    "fist":      [(55, 90), (55, 90), (55, 90), (55, 90), (55, 90)],
    "point":     [(55, 90), (0, 35),  (55, 90), (55, 90), (55, 90)],
    "peace":     [(55, 90), (0, 35),  (0, 35),  (55, 90), (55, 90)],
    "thumbs_up": [(0, 35),  (55, 90), (55, 90), (55, 90), (55, 90)],
    "pinch":     [(35, 90), (35, 90), (0, 40),  (0, 40),  (0, 40) ],
}

# Max Euclidean distance in 5D angle-space to count as a K-NN match
KNN_THRESHOLD = 22.0


def _euclidean(a: list, b: list) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


class GestureRecognizer:
    def __init__(self):
        self._refs: dict = {}
        self.reload()

    def reload(self):
        """Rebuild K-NN reference vectors from saved gesture files."""
        self._refs = {}
        for path in GESTURES_DIR.glob("*.json"):
            try:
                frames = json.loads(path.read_text())["frames"]
                if not frames:
                    continue
                n = len(frames)
                mean = [sum(f["angles"][i] for f in frames) / n for i in range(5)]
                self._refs[path.stem] = mean
            except (KeyError, IndexError, ValueError, json.JSONDecodeError):
                pass

    def recognize(self, angles: list) -> dict:
        # Layer 1: rule-based built-in poses
        for name, ranges in BUILTIN_POSES.items():
            if all(lo <= a <= hi for a, (lo, hi) in zip(angles, ranges)):
                return {"gesture": name, "source": "builtin", "confidence": 1.0}

        # Layer 2: K-NN over recorded gestures
        if self._refs:
            best_name = min(self._refs, key=lambda n: _euclidean(angles, self._refs[n]))
            best_dist = _euclidean(angles, self._refs[best_name])
            if best_dist <= KNN_THRESHOLD:
                confidence = round(1.0 - best_dist / KNN_THRESHOLD, 2)
                return {"gesture": best_name, "source": "recorded", "confidence": confidence}

        return {"gesture": None, "source": None, "confidence": 0.0}

    def known_gestures(self) -> list:
        return list(self._refs.keys())
