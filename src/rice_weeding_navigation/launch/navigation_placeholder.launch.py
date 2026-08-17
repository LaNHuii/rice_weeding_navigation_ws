from launch import LaunchDescription
from launch.actions import LogInfo


def generate_launch_description():
    return LaunchDescription([LogInfo(msg=(
        "rice_weeding_navigation is an interface stub: motion remains disabled "
        "until the Phase 2 simulator and safety chain are validated."))])
