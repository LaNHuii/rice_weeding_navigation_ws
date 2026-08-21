#!/usr/bin/python3
"""Wait for an expected Phase 3 localization diagnostic reason."""

import sys

import rclpy
from diagnostic_msgs.msg import DiagnosticArray
from rclpy.node import Node


class LocalizationStatusExpectation(Node):
    """Exit successfully once the expected diagnostic reason is observed."""

    def __init__(self):
        super().__init__("rice_weeding_localization_status_expectation")
        self.declare_parameter("expected_reason", "position_jump_detected")
        self.declare_parameter("timeout", 8.0)
        self._matched = False
        self._expected_reason = str(self.get_parameter("expected_reason").value)
        timeout = max(float(self.get_parameter("timeout").value), 0.1)
        self.create_subscription(
            DiagnosticArray,
            "/rice_weeding/localization/status",
            self._status_callback,
            10,
        )
        self.create_timer(timeout, self._timeout_callback)
        self.get_logger().info(
            f"Waiting for localization reason: {self._expected_reason}"
        )

    def _status_callback(self, message):
        for status in message.status:
            values = {item.key: item.value for item in status.values}
            reasons = [item for item in values.get("reasons", "").split(",") if item]
            if self._expected_reason in reasons:
                self._matched = True
                self.get_logger().info(
                    f"Observed expected localization reason: {self._expected_reason}"
                )
                rclpy.shutdown()

    def _timeout_callback(self):
        if not self._matched:
            self.get_logger().error(
                f"Timed out waiting for localization reason: {self._expected_reason}"
            )
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = LocalizationStatusExpectation()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    matched = node._matched
    try:
        node.destroy_node()
    except KeyboardInterrupt:
        pass
    sys.exit(0 if matched else 1)


if __name__ == "__main__":
    main()
