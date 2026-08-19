from pathlib import Path

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    description_share = Path(get_package_share_directory("rice_weeding_description"))
    profile = description_share / "profiles/platforms/rice_weeding_prototype.yaml"
    with profile.open("r", encoding="utf-8") as stream:
        platform = yaml.safe_load(stream)["platform"]
    limits = platform["limits"]
    safety = platform["safety"]

    return LaunchDescription([
        DeclareLaunchArgument("startup_motion_enabled", default_value="false"),
        Node(
            package="rice_weeding_safety",
            executable="velocity_safety_gate.py",
            name="rice_weeding_velocity_safety_gate",
            output="screen",
            parameters=[{
                "startup_motion_enabled": ParameterValue(
                    LaunchConfiguration("startup_motion_enabled"), value_type=bool
                ),
                "command_timeout": safety["command_timeout"],
                "publish_rate": safety["publish_rate"],
                "reject_nonplanar_twist": safety["reject_nonplanar_twist"],
                "nonplanar_epsilon": safety["nonplanar_epsilon"],
                "max_forward_velocity": limits["max_forward_velocity"],
                "max_reverse_velocity": limits["max_reverse_velocity"],
                "max_angular_velocity": limits["max_angular_velocity"],
            }],
        ),
    ])
