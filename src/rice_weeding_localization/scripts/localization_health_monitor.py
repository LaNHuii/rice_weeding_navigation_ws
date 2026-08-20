#!/usr/bin/python3
"""Publish Phase 3 localization health diagnostics without owning TF."""

import math

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Imu, NavSatFix, NavSatStatus

from localization_health_logic import (
    LocalizationHealthInput,
    LocalizationHealthThresholds,
    evaluate_localization_health,
)


class LocalizationHealthMonitor(Node):
    """Contract stub for future localization health gates."""

    def __init__(self):
        super().__init__("rice_weeding_localization_health_monitor")
        self.declare_parameter("thresholds_verified", False)
        self.declare_parameter("enforce_thresholds", False)
        self.declare_parameter("max_gnss_age", 0.0)
        self.declare_parameter("max_imu_age", 0.0)
        self.declare_parameter("max_wheel_odometry_age", 0.0)
        self.declare_parameter("max_fused_odometry_age", 0.0)
        self.declare_parameter("max_position_covariance", 0.0)
        self.declare_parameter("max_yaw_covariance", 0.0)
        self.declare_parameter("max_position_jump", 0.0)
        self.declare_parameter("publish_rate", 2.0)

        self._gnss_left = None
        self._gnss_right = None
        self._imu = None
        self._wheel_odometry = None
        self._fused_odometry = None
        self._previous_fused_position = None

        self.create_subscription(
            NavSatFix,
            "/rice_weeding/localization/gnss_left/fix",
            self._gnss_left_callback,
            10,
        )
        self.create_subscription(
            NavSatFix,
            "/rice_weeding/localization/gnss_right/fix",
            self._gnss_right_callback,
            10,
        )
        self.create_subscription(
            Imu,
            "/rice_weeding/localization/imu/data",
            self._imu_callback,
            10,
        )
        self.create_subscription(
            Odometry,
            "/rice_weeding/localization/wheel_odometry",
            self._wheel_odometry_callback,
            10,
        )
        self.create_subscription(
            Odometry,
            "/rice_weeding/localization/fused/odometry",
            self._fused_odometry_callback,
            10,
        )
        self._status_publisher = self.create_publisher(
            DiagnosticArray, "/rice_weeding/localization/status", 10
        )

        rate = max(float(self.get_parameter("publish_rate").value), 0.1)
        self.create_timer(1.0 / rate, self._publish_status)
        self.get_logger().info("Phase 3 localization health contract monitor started")

    def _gnss_left_callback(self, message):
        self._gnss_left = message

    def _gnss_right_callback(self, message):
        self._gnss_right = message

    def _imu_callback(self, message):
        self._imu = message

    def _wheel_odometry_callback(self, message):
        self._wheel_odometry = message

    def _fused_odometry_callback(self, message):
        self._fused_odometry = message

    def _message_age(self, message):
        if message is None:
            return None
        stamp = message.header.stamp
        stamp_seconds = stamp.sec + stamp.nanosec * 1.0e-9
        if stamp_seconds <= 0.0:
            return None
        now = self.get_clock().now().nanoseconds * 1.0e-9
        return max(0.0, now - stamp_seconds)

    def _is_fix_ok(self, message):
        return message is not None and message.status.status >= NavSatStatus.STATUS_FIX

    def _position_covariance(self):
        values = []
        for fix in (self._gnss_left, self._gnss_right):
            if fix is not None:
                values.extend(fix.position_covariance[index] for index in (0, 4))
        if self._fused_odometry is not None:
            values.extend(self._fused_odometry.pose.covariance[index] for index in (0, 7))
        finite_values = [value for value in values if math.isfinite(value) and value >= 0.0]
        return max(finite_values) if finite_values else None

    def _yaw_covariance(self):
        values = []
        if self._imu is not None:
            values.append(self._imu.orientation_covariance[8])
        if self._fused_odometry is not None:
            values.append(self._fused_odometry.pose.covariance[35])
        finite_values = [value for value in values if math.isfinite(value) and value >= 0.0]
        return max(finite_values) if finite_values else None

    def _position_jump(self):
        if self._fused_odometry is None:
            return None
        pose = self._fused_odometry.pose.pose.position
        current = (pose.x, pose.y, pose.z)
        previous = self._previous_fused_position
        self._previous_fused_position = current
        if previous is None:
            return 0.0
        return math.dist(previous, current)

    def _thresholds(self):
        def unset_zero(name):
            value = float(self.get_parameter(name).value)
            return value if value > 0.0 else None

        return LocalizationHealthThresholds(
            verified=bool(self.get_parameter("thresholds_verified").value),
            enforce=bool(self.get_parameter("enforce_thresholds").value),
            max_gnss_age=unset_zero("max_gnss_age"),
            max_imu_age=unset_zero("max_imu_age"),
            max_wheel_odometry_age=unset_zero("max_wheel_odometry_age"),
            max_fused_odometry_age=unset_zero("max_fused_odometry_age"),
            max_position_covariance=unset_zero("max_position_covariance"),
            max_yaw_covariance=unset_zero("max_yaw_covariance"),
            max_position_jump=unset_zero("max_position_jump"),
        )

    def _observation(self):
        return LocalizationHealthInput(
            gnss_left_fix_ok=self._is_fix_ok(self._gnss_left),
            gnss_right_fix_ok=self._is_fix_ok(self._gnss_right),
            gnss_left_age=self._message_age(self._gnss_left),
            gnss_right_age=self._message_age(self._gnss_right),
            imu_age=self._message_age(self._imu),
            wheel_odometry_age=self._message_age(self._wheel_odometry),
            fused_odometry_age=self._message_age(self._fused_odometry),
            position_covariance=self._position_covariance(),
            yaw_covariance=self._yaw_covariance(),
            position_jump=self._position_jump(),
        )

    def _publish_status(self):
        observation = self._observation()
        thresholds = self._thresholds()
        level, summary, reasons = evaluate_localization_health(observation, thresholds)

        status = DiagnosticStatus()
        status.name = "rice_weeding_localization_health"
        status.hardware_id = "phase3_interface_stub"
        status.level = bytes([level])
        status.message = summary
        status.values = [
            KeyValue(key="thresholds_verified", value=str(thresholds.verified).lower()),
            KeyValue(key="thresholds_enforced", value=str(thresholds.enforce).lower()),
            KeyValue(key="reasons", value=",".join(reasons)),
            KeyValue(key="gnss_left_fix_ok", value=str(observation.gnss_left_fix_ok).lower()),
            KeyValue(key="gnss_right_fix_ok", value=str(observation.gnss_right_fix_ok).lower()),
            KeyValue(key="position_covariance", value=str(observation.position_covariance)),
            KeyValue(key="yaw_covariance", value=str(observation.yaw_covariance)),
            KeyValue(key="position_jump", value=str(observation.position_jump)),
        ]

        message = DiagnosticArray()
        message.header.stamp = self.get_clock().now().to_msg()
        message.status.append(status)
        self._status_publisher.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = LocalizationHealthMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
