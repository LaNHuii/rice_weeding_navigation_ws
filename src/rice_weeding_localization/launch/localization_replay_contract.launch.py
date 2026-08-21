#!/usr/bin/python3
"""Start Phase 3 health monitor with simulation-only replay samples."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    scenario = LaunchConfiguration("scenario")
    return LaunchDescription([
        DeclareLaunchArgument("scenario", default_value="nominal"),
        Node(
            package="rice_weeding_localization",
            executable="localization_health_monitor.py",
            name="rice_weeding_localization_health_monitor",
            output="screen",
            parameters=[{
                "thresholds_verified": False,
                "enforce_thresholds": True,
                "max_gnss_age": 0.50,
                "max_imu_age": 0.50,
                "max_wheel_odometry_age": 0.50,
                "max_fused_odometry_age": 0.50,
                "max_position_covariance": 0.10,
                "max_yaw_covariance": 0.05,
                "max_position_jump": 0.20,
            }],
        ),
        Node(
            package="rice_weeding_localization",
            executable="localization_replay_sample_publisher.py",
            name="rice_weeding_localization_replay_sample_publisher",
            output="screen",
            parameters=[{
                "scenario": scenario,
                "stale_age": 2.0,
                "jump_distance": 1.0,
                "high_position_covariance": 0.25,
                "high_yaw_covariance": 0.10,
            }],
        ),
    ])
