#!/usr/bin/python3

"""Publish the simulation-only chassis odometry edge for the Phase 2 gate."""

import math

from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage
from tf2_ros import TransformBroadcaster


def _yaw_from_quaternion(quaternion):
    return math.atan2(
        2.0 * (quaternion.w * quaternion.z + quaternion.x * quaternion.y),
        1.0 - 2.0 * (quaternion.y * quaternion.y + quaternion.z * quaternion.z),
    )


def _normalize_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


class SimulationChassisOdometry(Node):
    """Adapt Gazebo model pose to the unique simulation odometry edge."""

    def __init__(self):
        super().__init__("rice_weeding_simulation_chassis_odometry")
        self.declare_parameter("model_name", "rice_weeding_robot")
        self.declare_parameter(
            "pose_info_topic", "/rice_weeding/simulation/pose_info"
        )
        self.declare_parameter(
            "odometry_topic", "/rice_weeding/localization/odometry"
        )
        self.declare_parameter("odom_frame", "odom")
        self.declare_parameter("base_frame", "base_footprint")
        self.declare_parameter("motion_enabled", False)

        self.model_name = self.get_parameter("model_name").value
        self.odom_frame = self.get_parameter("odom_frame").value
        self.base_frame = self.get_parameter("base_frame").value
        self.motion_enabled = self.get_parameter("motion_enabled").value

        self.odometry_publisher = self.create_publisher(
            Odometry, self.get_parameter("odometry_topic").value, 10
        )
        self.create_subscription(
            TFMessage,
            self.get_parameter("pose_info_topic").value,
            self._pose_info_callback,
            10,
        )
        self.tf_broadcaster = TransformBroadcaster(self)
        self._received_model_pose = False
        self._last_pose = None

    def _pose_info_callback(self, message):
        for transform in message.transforms:
            normalized_child = transform.child_frame_id.replace("::", "/")
            child_parts = [part for part in normalized_child.split("/") if part]
            if not child_parts or child_parts[-1] != self.model_name:
                continue

            stamp = self.get_clock().now().to_msg()
            odometry = Odometry()
            odometry.header.stamp = stamp
            odometry.header.frame_id = self.odom_frame
            odometry.child_frame_id = self.base_frame
            odometry.pose.pose.position.x = transform.transform.translation.x
            odometry.pose.pose.position.y = transform.transform.translation.y
            odometry.pose.pose.position.z = transform.transform.translation.z
            odometry.pose.pose.orientation = transform.transform.rotation
            stamp_seconds = stamp.sec + stamp.nanosec * 1.0e-9
            if self.motion_enabled and self._last_pose is not None:
                last_x, last_y, last_yaw, last_stamp = self._last_pose
                dt = stamp_seconds - last_stamp
                if dt > 1.0e-6:
                    yaw = _yaw_from_quaternion(transform.transform.rotation)
                    dx = transform.transform.translation.x - last_x
                    dy = transform.transform.translation.y - last_y
                    # nav_msgs/Odometry expresses Twist in child_frame_id.
                    odometry.twist.twist.linear.x = (
                        math.cos(yaw) * dx + math.sin(yaw) * dy
                    ) / dt
                    odometry.twist.twist.angular.z = _normalize_angle(yaw - last_yaw) / dt
            self.odometry_publisher.publish(odometry)

            chassis_tf = TransformStamped()
            chassis_tf.header.stamp = stamp
            chassis_tf.header.frame_id = self.odom_frame
            chassis_tf.child_frame_id = self.base_frame
            chassis_tf.transform.translation.x = transform.transform.translation.x
            chassis_tf.transform.translation.y = transform.transform.translation.y
            chassis_tf.transform.translation.z = transform.transform.translation.z
            chassis_tf.transform.rotation = transform.transform.rotation
            self.tf_broadcaster.sendTransform(chassis_tf)

            self._last_pose = (
                transform.transform.translation.x,
                transform.transform.translation.y,
                _yaw_from_quaternion(transform.transform.rotation),
                stamp_seconds,
            )

            if not self._received_model_pose:
                self.get_logger().info(
                    "Publishing simulation chassis odometry and %s -> %s for '%s' (%s)"
                    % (self.odom_frame, self.base_frame, self.model_name,
                       "motion enabled" if self.motion_enabled else "motion disabled")
                )
                self._received_model_pose = True
            return


def main(args=None):
    rclpy.init(args=args)
    node = SimulationChassisOdometry()
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
