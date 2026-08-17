from pathlib import Path

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _reject_motion(context):
    if LaunchConfiguration("motion_enabled").perform(context).lower() in {
        "1", "true", "yes", "on",
    }:
        raise RuntimeError(
            "Phase 2 entity-spawn gate is motion-disabled. Complete the velocity "
            "chain, explicit headland, safety gate and stop tests first."
        )
    return []


def generate_launch_description():
    simulation_share = Path(get_package_share_directory("rice_weeding_simulation"))
    environment_profile = simulation_share / "profiles/environments/paddy_field.yaml"
    with environment_profile.open("r", encoding="utf-8") as stream:
        environment = yaml.safe_load(stream)["environment"]

    spawn_pose = environment["simulation_spawn_pose"]
    surface_z = environment["terrain"]["surface_elevation"]

    return LaunchDescription([
        DeclareLaunchArgument("motion_enabled", default_value="false"),
        OpaqueFunction(function=_reject_motion),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                str(simulation_share / "launch/paddy_world.launch.py")
            )
        ),
        TimerAction(
            period=3.0,
            actions=[
                Node(
                    package="ros_gz_sim",
                    executable="create",
                    name="rice_weeding_robot_spawner",
                    output="screen",
                    arguments=[
                        "-name", "rice_weeding_robot",
                        "-topic", "robot_description",
                        "-x", str(spawn_pose["x"]),
                        "-y", str(spawn_pose["y"]),
                        "-z", str(surface_z),
                        "-Y", str(spawn_pose["yaw"]),
                    ],
                )
            ],
        ),
    ])
