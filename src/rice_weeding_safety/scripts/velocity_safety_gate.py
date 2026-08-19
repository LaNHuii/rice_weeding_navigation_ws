#!/usr/bin/python3
"""Fail-closed navigation velocity boundary for simulation and future chassis use."""

import time

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import Twist
from rclpy.node import Node

from velocity_safety_logic import evaluate_command


class VelocitySafetyGate(Node):
    def __init__(self):
        super().__init__("rice_weeding_velocity_safety_gate")
        self._motion_enabled = self.declare_parameter(
            "startup_motion_enabled", False
        ).value
        self._timeout = float(self.declare_parameter("command_timeout", 0.5).value)
        self._publish_rate = float(self.declare_parameter("publish_rate", 20.0).value)
        self._max_forward = float(
            self.declare_parameter("max_forward_velocity", 0.0).value
        )
        self._max_reverse = float(
            self.declare_parameter("max_reverse_velocity", 0.0).value
        )
        self._max_angular = float(
            self.declare_parameter("max_angular_velocity", 0.0).value
        )
        self._reject_nonplanar = bool(
            self.declare_parameter("reject_nonplanar_twist", True).value
        )
        self._nonplanar_epsilon = float(
            self.declare_parameter("nonplanar_epsilon", 1.0e-9).value
        )
        if self._timeout <= 0.0 or self._publish_rate <= 0.0:
            raise ValueError("command_timeout and publish_rate must be positive")
        if min(self._max_forward, self._max_reverse, self._max_angular) < 0.0:
            raise ValueError("velocity limits must be non-negative")

        self._command = None
        self._command_stamp = float("-inf")
        self._reason = "motion_disabled" if not self._motion_enabled else "input_timeout"
        self._safe_publisher = self.create_publisher(
            Twist, "/rice_weeding/safety/cmd_vel", 10
        )
        self._status_publisher = self.create_publisher(
            DiagnosticArray, "/rice_weeding/safety/status", 10
        )
        self.create_subscription(
            Twist,
            "/rice_weeding/navigation/cmd_vel_raw",
            self._command_callback,
            10,
        )
        # This node deliberately uses wall/monotonic time. A frozen /clock must
        # never preserve an old command or stop the watchdog timer.
        self.create_timer(1.0 / self._publish_rate, self._tick)
        if self._motion_enabled:
            self.get_logger().warning(
                "Motion was explicitly enabled for the simulation-only headland gate"
            )
        else:
            self.get_logger().info("Velocity safety gate started fail-closed")

    def _command_callback(self, message):
        self._command = (
            message.linear.x,
            message.linear.y,
            message.linear.z,
            message.angular.x,
            message.angular.y,
            message.angular.z,
        )
        self._command_stamp = time.monotonic()

    def _tick(self):
        now = time.monotonic()
        age = now - self._command_stamp
        linear, angular, self._reason = evaluate_command(
            self._command,
            age,
            self._motion_enabled,
            self._timeout,
            self._max_forward,
            self._max_reverse,
            self._max_angular,
            self._reject_nonplanar,
            self._nonplanar_epsilon,
        )
        output = Twist()
        output.linear.x = linear
        output.angular.z = angular
        self._safe_publisher.publish(output)
        self._publish_status(linear, angular)

    def _publish_status(self, linear, angular):
        status = DiagnosticStatus()
        status.name = "rice_weeding_safety/velocity_gate"
        status.hardware_id = "software_boundary"
        status.level = (
            DiagnosticStatus.OK
            if self._reason in ("command_ok", "command_limited")
            else DiagnosticStatus.WARN
        )
        status.message = self._reason
        status.values = [
            KeyValue(key="motion_enabled", value=str(self._motion_enabled).lower()),
            KeyValue(key="linear_output", value=f"{linear:.6f}"),
            KeyValue(key="angular_output", value=f"{angular:.6f}"),
            KeyValue(key="wall_clock_watchdog", value="true"),
        ]
        array = DiagnosticArray()
        array.header.stamp = self.get_clock().now().to_msg()
        array.status = [status]
        self._status_publisher.publish(array)


def main(args=None):
    rclpy.init(args=args)
    node = VelocitySafetyGate()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
