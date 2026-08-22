#!/usr/bin/python3
"""Publish a rice semantic GeoJSON as RViz MarkerArray preview."""

import argparse
from pathlib import Path
import sys

try:
    from ament_index_python.packages import get_package_share_directory
except ImportError:
    get_package_share_directory = None


def _add_package_to_path():
    if get_package_share_directory is not None:
        module_path = Path(get_package_share_directory("rice_weeding_semantics"))
    else:
        module_path = Path(__file__).resolve().parents[1]
    if str(module_path) not in sys.path:
        sys.path.insert(0, str(module_path))


_add_package_to_path()

import rclpy
from geometry_msgs.msg import Point
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from visualization_msgs.msg import Marker, MarkerArray

from rice_weeding_semantics.semantic_io import load_semantic_map


COLORS = {
    "field_boundary": (0.18, 0.62, 0.45, 0.95),
    "crop_row": (0.05, 0.72, 0.08, 0.95),
    "weed_patch": (0.85, 0.35, 0.10, 0.90),
    "hard_obstacle": (0.80, 0.10, 0.10, 0.95),
    "negative_obstacle": (0.28, 0.16, 0.70, 0.95),
    "headland_zone": (0.20, 0.55, 0.95, 0.45),
    "keepout_zone": (0.75, 0.15, 0.45, 0.80),
    "work_direction": (0.95, 0.85, 0.10, 0.95),
}
LINE_TYPES = {"crop_row", "work_direction"}


class SemanticMarkerPreview(Node):
    def __init__(self, semantic_map_path):
        super().__init__("rice_weeding_semantic_marker_preview")
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._publisher = self.create_publisher(
            MarkerArray, "/rice_weeding/semantics/markers", qos
        )
        self._markers = build_marker_array(load_semantic_map(semantic_map_path))
        self.create_timer(1.0, self._publish)
        self._publish()
        self.get_logger().info(f"Loaded semantic preview: {semantic_map_path}")

    def _publish(self):
        now = self.get_clock().now().to_msg()
        for marker in self._markers.markers:
            marker.header.stamp = now
        self._publisher.publish(self._markers)


def build_marker_array(semantic_map):
    markers = MarkerArray()
    delete_all = Marker()
    delete_all.action = Marker.DELETEALL
    markers.markers.append(delete_all)
    marker_id = 1
    for feature in semantic_map.features:
        if not feature.enabled:
            continue
        marker = _feature_marker(feature, marker_id)
        if marker is not None:
            markers.markers.append(marker)
            marker_id += 1
    return markers


def _feature_marker(feature, marker_id):
    if feature.geometry_type not in {"LineString", "Polygon"}:
        return None
    marker = Marker()
    marker.header.frame_id = feature.frame_id
    marker.ns = feature.feature_type
    marker.id = marker_id
    marker.action = Marker.ADD
    marker.pose.orientation.w = 1.0
    marker.scale.x = 0.04 if feature.feature_type in LINE_TYPES else 0.03
    red, green, blue, alpha = COLORS.get(feature.feature_type, (1.0, 1.0, 1.0, 0.8))
    marker.color.r = red
    marker.color.g = green
    marker.color.b = blue
    marker.color.a = alpha
    if feature.geometry_type == "LineString":
        marker.type = Marker.LINE_STRIP
        marker.points = [_point(point) for point in feature.coordinates]
    else:
        marker.type = Marker.LINE_STRIP
        marker.points = [_point(point) for point in feature.coordinates[0]]
    return marker


def _point(coordinate):
    point = Point()
    point.x = float(coordinate[0])
    point.y = float(coordinate[1])
    point.z = 0.08
    return point


def main():
    parser = argparse.ArgumentParser(description="Publish semantic GeoJSON as RViz markers.")
    parser.add_argument("--semantic-map", required=True)
    args = parser.parse_args()

    rclpy.init()
    node = SemanticMarkerPreview(args.semantic_map)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
