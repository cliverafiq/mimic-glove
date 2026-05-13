ADC_MIN = 0
ADC_MAX = 4095
ANGLE_MIN = 0.0
ANGLE_MAX = 90.0

# Per-finger calibration: (raw_flat, raw_fist)
# Defaults assume full ADC range maps to flat→fist.
DEFAULT_CALIBRATION = [
    (200, 3800),
    (200, 3800),
    (200, 3800),
    (200, 3800),
    (200, 3800),
]


def parse(packet: dict, calibration: list = DEFAULT_CALIBRATION) -> dict:
    angles = []
    for i, raw in enumerate(packet["channels"]):
        flat, fist = calibration[i]
        normalized = (raw - flat) / max(fist - flat, 1)
        normalized = max(0.0, min(1.0, normalized))
        angle = normalized * ANGLE_MAX
        angles.append(round(angle, 2))
    return {"timestamp": packet["timestamp"], "angles": angles}
