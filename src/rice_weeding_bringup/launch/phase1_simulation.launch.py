from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def _reject_motion(context):
    if LaunchConfiguration("motion_enabled").perform(context).lower() in {"1", "true", "yes", "on"}:
        raise RuntimeError(
            "Phase 1 is scene/TF-only. motion_enabled must remain false until the "
            "simulator, safety chain and stop tests are complete.")
    return []


def generate_launch_description():
    simulation_share = Path(get_package_share_directory("rice_weeding_simulation"))
    return LaunchDescription([
        DeclareLaunchArgument("motion_enabled", default_value="false"),
        OpaqueFunction(function=_reject_motion),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            str(simulation_share / "launch" / "paddy_world.launch.py"))),
    ])
