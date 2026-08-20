#!/usr/bin/python3
"""Start the Phase 3 localization health contract stub."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="rice_weeding_localization",
            executable="localization_health_monitor.py",
            name="rice_weeding_localization_health_monitor",
            output="screen",
            parameters=[{
                "thresholds_verified": False,
                "enforce_thresholds": False,
            }],
        )
    ])
