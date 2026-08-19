"""Phase 2 simulation plus the constrained, safety-gated Nav2 entry point."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    bringup_share = Path(get_package_share_directory("rice_weeding_bringup"))
    navigation_share = Path(get_package_share_directory("rice_weeding_navigation"))
    return LaunchDescription([
        DeclareLaunchArgument("motion_enabled", default_value="false"),
        DeclareLaunchArgument("headless", default_value="false"),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                str(bringup_share / "launch/phase2_simulation.launch.py")
            ),
            launch_arguments={
                "motion_enabled": LaunchConfiguration("motion_enabled"),
                "headless": LaunchConfiguration("headless"),
            }.items(),
        ),
        TimerAction(
            period=6.0,
            actions=[IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(navigation_share / "launch/phase2_navigation.launch.py")
                )
            )],
        ),
    ])
