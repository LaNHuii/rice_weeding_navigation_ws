#!/usr/bin/python3

"""Adapt the selected Gazebo model pose to the Phase 2 truth contract."""

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from tf2_msgs.msg import TFMessage
from tf2_ros import StaticTransformBroadcaster
from geometry_msgs.msg import TransformStamped


class SimulationTruthAdapter(Node):
    """Publish simulation-only truth without claiming chassis odometry ownership."""

    def __init__(self):
        super().__init__("rice_weeding_simulation_truth_adapter")
        self.declare_parameter("model_name", "rice_weeding_robot")
        self.declare_parameter(
            "pose_info_topic", "/rice_weeding/simulation/pose_info"
        )
        self.declare_parameter(
            "ground_truth_topic", "/rice_weeding/simulation/ground_truth"
        )
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("odom_frame", "odom")
        self.declare_parameter("base_frame", "base_footprint")
        self.declare_parameter("world_to_map_x", 0.0)
        self.declare_parameter("world_to_map_y", 0.0)

        self.model_name = self.get_parameter("model_name").value
        self.map_frame = self.get_parameter("map_frame").value
        self.odom_frame = self.get_parameter("odom_frame").value
        self.base_frame = self.get_parameter("base_frame").value
        self.world_to_map_x = self.get_parameter("world_to_map_x").value
        self.world_to_map_y = self.get_parameter("world_to_map_y").value

        self.truth_publisher = self.create_publisher(
            Odometry, self.get_parameter("ground_truth_topic").value, 10
        )
        self.create_subscription(
            TFMessage,
            self.get_parameter("pose_info_topic").value,
            self._pose_info_callback,
            10,
        )

        self.static_tf_broadcaster = StaticTransformBroadcaster(self)
        self._publish_map_to_odom()
        self._received_model_pose = False

    def _publish_map_to_odom(self):
        transform = TransformStamped()
        transform.header.stamp = self.get_clock().now().to_msg()
        transform.header.frame_id = self.map_frame
        transform.child_frame_id = self.odom_frame
        transform.transform.translation.x = self.world_to_map_x
        transform.transform.translation.y = self.world_to_map_y
        transform.transform.rotation.w = 1.0
        self.static_tf_broadcaster.sendTransform(transform)

    def _pose_info_callback(self, message):
        for transform in message.transforms:
            normalized_child = transform.child_frame_id.replace("::", "/")
            child_parts = [part for part in normalized_child.split("/") if part]
            if not child_parts or child_parts[-1] != self.model_name:
                continue

            truth = Odometry()
            # Fortress' Pose_V -> TFMessage bridge does not propagate the
            # vector-level Gazebo stamp into each transform. Timestamp the
            # sample with the bridged simulation clock on receipt instead.
            truth.header.stamp = self.get_clock().now().to_msg()
            truth.header.frame_id = self.map_frame
            truth.child_frame_id = self.base_frame
            truth.pose.pose.position.x = (
                transform.transform.translation.x + self.world_to_map_x
            )
            truth.pose.pose.position.y = (
                transform.transform.translation.y + self.world_to_map_y
            )
            truth.pose.pose.position.z = transform.transform.translation.z
            truth.pose.pose.orientation = transform.transform.rotation
            self.truth_publisher.publish(truth)

            if not self._received_model_pose:
                self.get_logger().info(
                    "Publishing Gazebo truth for model '%s' as %s -> %s "
                    "with world offset (%.3f, %.3f)"
                    % (
                        self.model_name,
                        self.map_frame,
                        self.base_frame,
                        self.world_to_map_x,
                        self.world_to_map_y,
                    )
                )
                self._received_model_pose = True
            return


def main(args=None):
    rclpy.init(args=args)
    node = SimulationTruthAdapter()
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
