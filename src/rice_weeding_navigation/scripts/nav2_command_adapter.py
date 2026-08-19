#!/usr/bin/python3
"""Adapt Nav2's standard output topic to the project's raw safety input."""

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class Nav2CommandAdapter(Node):
    """This adapter performs no authorization, limiting, or Gazebo bridging."""

    def __init__(self):
        super().__init__("rice_weeding_nav2_command_adapter")
        self._publisher = self.create_publisher(
            Twist, "/rice_weeding/navigation/cmd_vel_raw", 10
        )
        self.create_subscription(Twist, "/cmd_vel", self._callback, 10)
        self.get_logger().info("Forwarding Nav2 /cmd_vel only to the raw safety input")

    def _callback(self, message):
        self._publisher.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = Nav2CommandAdapter()
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
