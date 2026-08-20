"""Phase 3 localization interface and health contract entry point."""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    localization_share = Path(get_package_share_directory("rice_weeding_localization"))
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                str(localization_share / "launch/localization_health_contract.launch.py")
            )
        ),
    ])
