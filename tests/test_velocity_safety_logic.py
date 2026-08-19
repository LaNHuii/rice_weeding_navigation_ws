import importlib.util
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGIC_PATH = (
    ROOT / "src/rice_weeding_safety/scripts/velocity_safety_logic.py"
)
SPEC = importlib.util.spec_from_file_location("velocity_safety_logic", LOGIC_PATH)
LOGIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOGIC)


def evaluate(command, age=0.0, enabled=True):
    return LOGIC.evaluate_command(
        command=command,
        command_age=age,
        motion_enabled=enabled,
        timeout=0.5,
        max_forward=0.25,
        max_reverse=0.10,
        max_angular=0.35,
    )


def test_gate_starts_disabled_and_stale_input_stops_immediately():
    assert evaluate((0.1, 0.0, 0.0, 0.0, 0.0, 0.1), enabled=False) == (
        0.0, 0.0, "motion_disabled"
    )
    assert evaluate((0.1, 0.0, 0.0, 0.0, 0.0, 0.1), age=0.501) == (
        0.0, 0.0, "input_timeout"
    )
    assert evaluate(None) == (0.0, 0.0, "input_timeout")


def test_gate_limits_only_fresh_planar_commands():
    assert evaluate((0.12, 0.0, 0.0, 0.0, 0.0, -0.2)) == (
        0.12, -0.2, "command_ok"
    )
    assert evaluate((0.8, 0.0, 0.0, 0.0, 0.0, -0.8)) == (
        0.25, -0.35, "command_limited"
    )
    assert evaluate((-0.8, 0.0, 0.0, 0.0, 0.0, 0.0)) == (
        -0.10, 0.0, "command_limited"
    )


def test_gate_rejects_nonfinite_and_nonplanar_commands():
    assert evaluate((math.nan, 0.0, 0.0, 0.0, 0.0, 0.0)) == (
        0.0, 0.0, "invalid_input"
    )
    assert evaluate((0.1, 0.01, 0.0, 0.0, 0.0, 0.0)) == (
        0.0, 0.0, "nonplanar_input"
    )
