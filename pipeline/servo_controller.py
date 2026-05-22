"""
Maps finger angles (0–90°) to PCA9685 PWM ticks.

PCA9685 at 50Hz: 20ms period, 12-bit resolution (0–4095 ticks)
Servo pulse: 1ms (0°) → 2ms (180°)
  0°   = 1ms / 20ms * 4096 ≈ 205 ticks
  90°  = 1.5ms / 20ms * 4096 ≈ 307 ticks
  180° = 2ms / 20ms * 4096 ≈ 410 ticks
We use 0–90°, so we span TICK_MIN (205) → TICK_MAX_90 (307).
"""

TICK_MIN    = 205   # 0°
TICK_MAX_90 = 307   # 90°  (half of the full 0–180° servo range)
ANGLE_MAX   = 90.0
FINGER_NAMES = ["thumb", "index", "middle", "ring", "pinky"]


def angle_to_pwm(angle: float) -> int:
    clamped = max(0.0, min(ANGLE_MAX, angle))
    normalized = clamped / ANGLE_MAX
    tick = TICK_MIN + normalized * (TICK_MAX_90 - TICK_MIN)
    return round(tick)


def compute_servo_state(parsed: dict) -> dict:
    servos = []
    for i, angle in enumerate(parsed["angles"]):
        tick = angle_to_pwm(angle)
        servos.append({
            "finger": FINGER_NAMES[i],
            "angle": angle,
            "pwm_tick": tick,
        })
    return {
        "timestamp": parsed["timestamp"],
        "servos": servos,
    }
