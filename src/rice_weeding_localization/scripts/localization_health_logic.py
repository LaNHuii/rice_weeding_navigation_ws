#!/usr/bin/python3
"""ROS-independent Phase 3 localization health contract logic."""

from dataclasses import dataclass
import math


OK = 0
WARN = 1
ERROR = 2


@dataclass(frozen=True)
class LocalizationHealthInput:
    """Observed state for one localization-health evaluation cycle."""

    gnss_left_fix_ok: bool = False
    gnss_right_fix_ok: bool = False
    gnss_left_age: float | None = None
    gnss_right_age: float | None = None
    imu_age: float | None = None
    wheel_odometry_age: float | None = None
    fused_odometry_age: float | None = None
    position_covariance: float | None = None
    yaw_covariance: float | None = None
    position_jump: float | None = None


@dataclass(frozen=True)
class LocalizationHealthThresholds:
    """Unverified thresholds. They must not be treated as real safety limits."""

    verified: bool = False
    enforce: bool = False
    max_gnss_age: float | None = None
    max_imu_age: float | None = None
    max_wheel_odometry_age: float | None = None
    max_fused_odometry_age: float | None = None
    max_position_covariance: float | None = None
    max_yaw_covariance: float | None = None
    max_position_jump: float | None = None


def _finite_or_none(value):
    if value is None:
        return None
    return value if math.isfinite(value) else None


def _has_missing_input(observation):
    ages = (
        observation.gnss_left_age,
        observation.gnss_right_age,
        observation.imu_age,
        observation.wheel_odometry_age,
        observation.fused_odometry_age,
    )
    return any(_finite_or_none(age) is None for age in ages)


def _threshold_exceeded(value, threshold):
    value = _finite_or_none(value)
    threshold = _finite_or_none(threshold)
    return value is not None and threshold is not None and value > threshold


def evaluate_localization_health(observation, thresholds):
    """Return ``(level, summary, reasons)`` for the current contract state."""

    reasons = []
    if not thresholds.verified:
        reasons.append("thresholds_unverified")
    if not (observation.gnss_left_fix_ok and observation.gnss_right_fix_ok):
        reasons.append("rtk_fix_unavailable")
    if _has_missing_input(observation):
        reasons.append("input_missing")

    if thresholds.enforce:
        checks = (
            ("gnss_left_stale", observation.gnss_left_age, thresholds.max_gnss_age),
            ("gnss_right_stale", observation.gnss_right_age, thresholds.max_gnss_age),
            ("imu_stale", observation.imu_age, thresholds.max_imu_age),
            (
                "wheel_odometry_stale",
                observation.wheel_odometry_age,
                thresholds.max_wheel_odometry_age,
            ),
            (
                "fused_odometry_stale",
                observation.fused_odometry_age,
                thresholds.max_fused_odometry_age,
            ),
            (
                "position_covariance_high",
                observation.position_covariance,
                thresholds.max_position_covariance,
            ),
            (
                "yaw_covariance_high",
                observation.yaw_covariance,
                thresholds.max_yaw_covariance,
            ),
            (
                "position_jump_detected",
                observation.position_jump,
                thresholds.max_position_jump,
            ),
        )
        reasons.extend(name for name, value, limit in checks if _threshold_exceeded(value, limit))

    if any(reason != "thresholds_unverified" for reason in reasons):
        level = WARN
    else:
        level = OK
    summary = "localization_health_contract_ok" if level == OK else "localization_health_contract_warn"
    return level, summary, reasons
