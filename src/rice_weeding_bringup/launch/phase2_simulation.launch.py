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
from launch_ros.parameter_descriptions import ParameterValue


def _validate_motion(context, environment, required_headland_width):
    if LaunchConfiguration("motion_enabled").perform(context).lower() in {
        "1", "true", "yes", "on",
    }:
        field = environment["field"]
        crop_grid = environment["crop_grid"]
        if field["headland_width"] < required_headland_width:
            raise RuntimeError("Motion requires the platform-profile minimum headland width.")
        if not crop_grid["full_inner_coverage"]["motion_compatible"]:
            raise RuntimeError("Motion requires a crop layout marked motion-compatible.")
    return []


def generate_launch_description():
    simulation_share = Path(get_package_share_directory("rice_weeding_simulation"))
    safety_share = Path(get_package_share_directory("rice_weeding_safety"))
    description_share = Path(get_package_share_directory("rice_weeding_description"))
    environment_profile = simulation_share / "profiles/environments/paddy_field.yaml"
    with environment_profile.open("r", encoding="utf-8") as stream:
        environment = yaml.safe_load(stream)["environment"]
    platform_profile = description_share / "profiles/platforms/rice_weeding_prototype.yaml"
    with platform_profile.open("r", encoding="utf-8") as stream:
        required_headland_width = yaml.safe_load(stream)["platform"]["coverage"][
            "required_headland_width"
        ]

    spawn_pose = environment["simulation_spawn_pose"]
    field = environment["field"]
    world_to_map_x = 0.5 * field["boundary_outer_length"]
    world_to_map_y = 0.5 * field["boundary_outer_width"]
    surface_z = environment["terrain"]["surface_elevation"]

    return LaunchDescription([
        DeclareLaunchArgument("motion_enabled", default_value="false"),
        DeclareLaunchArgument("headless", default_value="false"),
        OpaqueFunction(
            function=_validate_motion,
            kwargs={
                "environment": environment,
                "required_headland_width": required_headland_width,
            },
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                str(simulation_share / "launch/paddy_world.launch.py")
            ),
            launch_arguments={"headless": LaunchConfiguration("headless")}.items(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                str(safety_share / "launch/safety_gate.launch.py")
            ),
            launch_arguments={
                "startup_motion_enabled": LaunchConfiguration("motion_enabled")
            }.items(),
        ),
        Node(
            package="rice_weeding_simulation",
            executable="simulation_truth_adapter.py",
            name="rice_weeding_simulation_truth_adapter",
            output="screen",
            parameters=[
                {"use_sim_time": True},
                {"world_to_map_x": world_to_map_x},
                {"world_to_map_y": world_to_map_y},
            ],
        ),
        Node(
            package="rice_weeding_simulation",
            executable="simulation_chassis_odometry.py",
            name="rice_weeding_simulation_chassis_odometry",
            output="screen",
            parameters=[
                {"use_sim_time": True},
                {"motion_enabled": ParameterValue(
                    LaunchConfiguration("motion_enabled"), value_type=bool
                )},
            ],
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
