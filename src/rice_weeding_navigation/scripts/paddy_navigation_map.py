#!/usr/bin/python3
"""Publish the profile-derived, static Nav2 map for the simulation field."""

from pathlib import Path

import rclpy
from nav_msgs.msg import OccupancyGrid
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
import yaml


class PaddyNavigationMap(Node):
    """Represent only hard field boundaries; crops remain a semantic layer."""

    def __init__(self):
        super().__init__("rice_weeding_paddy_navigation_map")
        self.declare_parameter("environment_profile", "")
        self.declare_parameter("resolution", 0.05)
        profile_path = Path(self.get_parameter("environment_profile").value)
        resolution = float(self.get_parameter("resolution").value)
        if not profile_path.is_file():
            raise ValueError("environment_profile must name an existing YAML file")
        if resolution <= 0.0:
            raise ValueError("resolution must be positive")

        with profile_path.open("r", encoding="utf-8") as stream:
            environment = yaml.safe_load(stream)["environment"]
        field = environment["field"]
        semantics = environment["semantic_classes"]
        if semantics["crops_are_navigation_obstacles"]:
            raise ValueError("This static map must not encode crops as obstacles")

        length = float(field["boundary_outer_length"])
        width = float(field["boundary_outer_width"])
        bund_thickness = float(field["bund"]["thickness"])
        cells_x = round(length / resolution)
        cells_y = round(width / resolution)
        if abs(cells_x * resolution - length) > 1.0e-9:
            raise ValueError("field length must be divisible by map resolution")
        if abs(cells_y * resolution - width) > 1.0e-9:
            raise ValueError("field width must be divisible by map resolution")

        map_message = OccupancyGrid()
        map_message.header.frame_id = environment["frame_id"]
        map_message.info.resolution = resolution
        map_message.info.width = cells_x
        map_message.info.height = cells_y
        map_message.info.origin.orientation.w = 1.0
        cells = []
        for cell_y in range(cells_y):
            y = (cell_y + 0.5) * resolution
            for cell_x in range(cells_x):
                x = (cell_x + 0.5) * resolution
                is_bund = (
                    x < bund_thickness
                    or x >= length - bund_thickness
                    or y < bund_thickness
                    or y >= width - bund_thickness
                )
                cells.append(100 if is_bund else 0)
        map_message.data = cells
        self._map_message = map_message
        self._publisher = self.create_publisher(
            OccupancyGrid,
            "/map",
            QoSProfile(
                depth=1,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE,
            ),
        )
        self.create_timer(1.0, self._publish)
        self.get_logger().info(
            "Publishing %dx%d profile-derived map; only field bund is occupied"
            % (cells_x, cells_y)
        )

    def _publish(self):
        now = self.get_clock().now()
        self._map_message.header.stamp = now.to_msg()
        self._map_message.info.map_load_time = (now - Duration(seconds=0)).to_msg()
        self._publisher.publish(self._map_message)


def main(args=None):
    rclpy.init(args=args)
    node = PaddyNavigationMap()
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
