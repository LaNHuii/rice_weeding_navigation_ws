# Phase 3 localization replay checks

This document records the Phase 3 localization-health replay contract. It does
not describe a real RTK receiver, RTK base station, fusion filter or chassis
output.

## Replay scenarios

Start one scenario in the first terminal:

```bash
cd ~/桌面/rice_weeding_navigation_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch rice_weeding_bringup phase3_localization_replay.launch.py scenario:=jump
```

Check one expected diagnostic reason in the second terminal:

```bash
cd ~/桌面/rice_weeding_navigation_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run rice_weeding_localization localization_status_expect.py --ros-args -p expected_reason:=position_jump_detected
```

Scenario to expected-reason mapping:

| Scenario | Expected diagnostic reason |
| --- | --- |
| `nominal` | only `thresholds_unverified` |
| `no_fix` | `rtk_fix_unavailable` |
| `left_no_fix` | `gnss_left_fix_unavailable` |
| `right_no_fix` | `gnss_right_fix_unavailable` |
| `high_covariance` | `position_covariance_high` or `yaw_covariance_high` |
| `stale` | one or more `*_stale` reasons |
| `jump` | `position_jump_detected` |

All thresholds in replay are contract values with `verified: false`; they are
not field safety limits.

## Extrinsics contract

Phase 3 consumes fixed sensor frames from `robot_description`. Current values
are simulation assumptions from the platform profile:

| Frame | Parent | xyz in parent frame | Status |
| --- | --- | --- | --- |
| `imu_link` | `base_link` | `[0.0, 0.0, 0.0]` | unverified |
| `gnss_left_link` | `base_link` | `[0.0, 0.35, 0.42]` | unverified |
| `gnss_right_link` | `base_link` | `[0.0, -0.35, 0.42]` | unverified |

The GNSS antenna height is `0.65 m` above `base_footprint` in the simulation
profile. The baseline is `0.70 m`. Real antenna phase centers, IMU mounting
orientation and cable/driver latency must be measured before real localization
or safety decisions use these values.

## Future rosbag recording contract

When real hardware exists, record at least:

```bash
ros2 bag record \
  /tf \
  /tf_static \
  /rice_weeding/localization/gnss_left/fix \
  /rice_weeding/localization/gnss_right/fix \
  /rice_weeding/localization/imu/data \
  /rice_weeding/localization/wheel_odometry \
  /rice_weeding/localization/fused/odometry \
  /rice_weeding/localization/status
```

Do not include `/rice_weeding/simulation/ground_truth` in real-system bags.
Do not include `/rice_weeding/safety/cmd_vel` unless the test is explicitly a
motion-safety test with separate approval and field precautions.
