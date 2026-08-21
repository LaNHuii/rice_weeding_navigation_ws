"""Phase 3 localization replay contract entry point."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    localization_share = Path(get_package_share_directory("rice_weeding_localization"))
    return LaunchDescription([
        DeclareLaunchArgument("scenario", default_value="nominal"),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                str(localization_share / "launch/localization_replay_contract.launch.py")
            ),
            launch_arguments={"scenario": LaunchConfiguration("scenario")}.items(),
        ),
    ])
