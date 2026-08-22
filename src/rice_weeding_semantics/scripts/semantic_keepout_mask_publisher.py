#!/usr/bin/python3
"""Publish a simulation-only semantic keepout mask as OccupancyGrid."""

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
from nav_msgs.msg import OccupancyGrid
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from rice_weeding_semantics.semantic_io import load_semantic_map
from rice_weeding_semantics.semantic_mask import (
    build_keepout_mask,
    geometry_from_semantic_bounds,
)


DEFAULT_TOPIC = "/rice_weeding/semantics/keepout_mask"


class SemanticKeepoutMaskPublisher(Node):
    def __init__(self, semantic_map_path, resolution, padding, topic):
        super().__init__("rice_weeding_semantic_keepout_mask_publisher")
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        semantic_map = load_semantic_map(semantic_map_path)
        geometry = geometry_from_semantic_bounds(
            semantic_map,
            resolution=resolution,
            padding=padding,
        )
        mask = build_keepout_mask(semantic_map, geometry)
        self._message = _to_occupancy_grid(mask)
        self._publisher = self.create_publisher(OccupancyGrid, topic, qos)
        self.create_timer(1.0, self._publish)
        self._publish()
        self.get_logger().warning(
            "Publishing simulation-only, unverified semantic keepout mask on "
            f"{topic}; crop_row and weed_patch are excluded from default obstacles"
        )

    def _publish(self):
        now = self.get_clock().now().to_msg()
        self._message.header.stamp = now
        self._message.info.map_load_time = now
        self._publisher.publish(self._message)


def _to_occupancy_grid(mask):
    message = OccupancyGrid()
    message.header.frame_id = mask.frame_id
    message.info.resolution = mask.resolution
    message.info.width = mask.width
    message.info.height = mask.height
    message.info.origin.position.x = mask.origin_x
    message.info.origin.position.y = mask.origin_y
    message.info.origin.position.z = 0.0
    message.info.origin.orientation.w = 1.0
    message.data = list(mask.data)
    return message


def main():
    parser = argparse.ArgumentParser(
        description="Publish semantic GeoJSON keepout mask as OccupancyGrid."
    )
    parser.add_argument("--semantic-map", required=True)
    parser.add_argument("--resolution", type=float, default=0.1)
    parser.add_argument("--padding", type=float, default=0.0)
    parser.add_argument("--topic", default=DEFAULT_TOPIC)
    parser.add_argument(
        "--acknowledge-simulation-only",
        action="store_true",
        help="Required guard: this publisher is not field-validated and does not enable Nav2.",
    )
    args = parser.parse_args()
    if not args.acknowledge_simulation_only:
        parser.error("--acknowledge-simulation-only is required for this Phase 4 publisher")

    rclpy.init()
    node = SemanticKeepoutMaskPublisher(
        args.semantic_map,
        resolution=args.resolution,
        padding=args.padding,
        topic=args.topic,
    )
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
