#!/usr/bin/python3
"""ROS-independent decision logic for the rice-weeding velocity safety gate."""

import math


def clamp(value, lower, upper):
    return min(max(value, lower), upper)


def evaluate_command(
    command,
    command_age,
    motion_enabled,
    timeout,
    max_forward,
    max_reverse,
    max_angular,
    reject_nonplanar=True,
    nonplanar_epsilon=1.0e-9,
):
    """Return ``(linear_x, angular_z, reason)`` for one safety cycle.

    ``command`` is either ``None`` or the six Twist components in the order
    linear x/y/z then angular x/y/z. Disabling, invalid input and timeout are
    immediate-stop conditions; only a fresh planar command can pass.
    """
    if not motion_enabled:
        return 0.0, 0.0, "motion_disabled"
    if command is None or command_age > timeout:
        return 0.0, 0.0, "input_timeout"
    if len(command) != 6 or not all(math.isfinite(value) for value in command):
        return 0.0, 0.0, "invalid_input"
    if reject_nonplanar and any(
        abs(command[index]) > nonplanar_epsilon for index in (1, 2, 3, 4)
    ):
        return 0.0, 0.0, "nonplanar_input"

    linear = clamp(command[0], -max_reverse, max_forward)
    angular = clamp(command[5], -max_angular, max_angular)
    reason = "command_limited" if (linear != command[0] or angular != command[5]) else "command_ok"
    return linear, angular, reason
