#!/usr/bin/python3
"""Publish simulation-only Phase 3 localization replay samples."""

import math

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Imu, NavSatFix, NavSatStatus


class LocalizationReplaySamplePublisher(Node):
    """Deterministic sample publisher for the localization health contract."""

    def __init__(self):
        super().__init__("rice_weeding_localization_replay_sample_publisher")
        self.declare_parameter("scenario", "nominal")
        self.declare_parameter("publish_rate", 5.0)
        self.declare_parameter("stale_age", 2.0)
        self.declare_parameter("jump_distance", 1.0)
        self.declare_parameter("high_position_covariance", 0.25)
        self.declare_parameter("high_yaw_covariance", 0.10)

        self._tick = 0
        self._gnss_left_pub = self.create_publisher(
            NavSatFix, "/rice_weeding/localization/gnss_left/fix", 10
        )
        self._gnss_right_pub = self.create_publisher(
            NavSatFix, "/rice_weeding/localization/gnss_right/fix", 10
        )
        self._imu_pub = self.create_publisher(
            Imu, "/rice_weeding/localization/imu/data", 10
        )
        self._wheel_odometry_pub = self.create_publisher(
            Odometry, "/rice_weeding/localization/wheel_odometry", 10
        )
        self._fused_odometry_pub = self.create_publisher(
            Odometry, "/rice_weeding/localization/fused/odometry", 10
        )

        rate = max(float(self.get_parameter("publish_rate").value), 0.1)
        self.create_timer(1.0 / rate, self._publish_samples)
        self.get_logger().info("Phase 3 localization replay sample publisher started")

    def _stamp(self, stale=False):
        now = self.get_clock().now()
        if stale:
            stale_age = float(self.get_parameter("stale_age").value)
            now = now - rclpy.duration.Duration(seconds=stale_age)
        return now.to_msg()

    def _scenario(self):
        return str(self.get_parameter("scenario").value)

    def _publish_samples(self):
        scenario = self._scenario()
        stale = scenario == "stale"
        no_fix = scenario == "no_fix"
        left_no_fix = no_fix or scenario == "left_no_fix"
        right_no_fix = no_fix or scenario == "right_no_fix"
        high_covariance = scenario == "high_covariance"
        stamp = self._stamp(stale=stale)

        self._gnss_left_pub.publish(
            self._fix(stamp, y_offset=0.35, no_fix=left_no_fix, high_covariance=high_covariance)
        )
        self._gnss_right_pub.publish(
            self._fix(stamp, y_offset=-0.35, no_fix=right_no_fix, high_covariance=high_covariance)
        )
        self._imu_pub.publish(self._imu(stamp, high_covariance=high_covariance))
        self._wheel_odometry_pub.publish(self._odometry(stamp, x=0.0))
        self._fused_odometry_pub.publish(
            self._odometry(
                stamp,
                x=self._fused_x(scenario),
                high_covariance=high_covariance,
            )
        )
        self._tick += 1

    def _fix(self, stamp, y_offset, no_fix=False, high_covariance=False):
        message = NavSatFix()
        message.header.stamp = stamp
        message.header.frame_id = "map"
        message.status.status = (
            NavSatStatus.STATUS_NO_FIX if no_fix else NavSatStatus.STATUS_FIX
        )
        message.status.service = NavSatStatus.SERVICE_GPS
        message.latitude = 30.0
        message.longitude = 120.0 + y_offset * 1.0e-6
        message.altitude = 10.0
        message.position_covariance_type = NavSatFix.COVARIANCE_TYPE_DIAGONAL_KNOWN
        position_covariance = (
            float(self.get_parameter("high_position_covariance").value)
            if high_covariance else 0.04
        )
        message.position_covariance[0] = position_covariance
        message.position_covariance[4] = position_covariance
        message.position_covariance[8] = 0.09
        return message

    def _imu(self, stamp, high_covariance=False):
        message = Imu()
        message.header.stamp = stamp
        message.header.frame_id = "imu_link"
        message.orientation.w = 1.0
        message.orientation_covariance[8] = (
            float(self.get_parameter("high_yaw_covariance").value)
            if high_covariance else 0.01
        )
        return message

    def _odometry(self, stamp, x, high_covariance=False):
        message = Odometry()
        message.header.stamp = stamp
        message.header.frame_id = "map"
        message.child_frame_id = "base_footprint"
        message.pose.pose.position.x = x
        message.pose.pose.position.y = 7.5
        message.pose.pose.position.z = 0.05
        message.pose.pose.orientation.w = 1.0
        position_covariance = (
            float(self.get_parameter("high_position_covariance").value)
            if high_covariance else 0.04
        )
        yaw_covariance = (
            float(self.get_parameter("high_yaw_covariance").value)
            if high_covariance else 0.01
        )
        message.pose.covariance[0] = position_covariance
        message.pose.covariance[7] = position_covariance
        message.pose.covariance[35] = yaw_covariance
        return message

    def _fused_x(self, scenario):
        if scenario != "jump":
            return 10.0
        jump_distance = abs(float(self.get_parameter("jump_distance").value))
        return 10.0 + (jump_distance if self._tick % 2 else 0.0)


def main(args=None):
    rclpy.init(args=args)
    node = LocalizationReplaySamplePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            try:
                rclpy.shutdown()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
