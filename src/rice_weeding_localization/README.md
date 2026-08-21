# rice_weeding_localization

Phase 3 localization interface package.

This package defines the future localization health boundary for dual GNSS,
IMU, wheel odometry and fused odometry. It does not connect real devices,
does not implement a fusion filter and does not publish TF.

Current executable:

- `localization_health_monitor.py`: subscribes to the planned localization
  inputs and publishes `/rice_weeding/localization/status`.
- `localization_replay_sample_publisher.py`: publishes simulation-only replay
  samples for nominal, no-fix, single-antenna no-fix, high-covariance, stale
  and position-jump contract checks.
- `localization_status_expect.py`: waits for one expected diagnostic reason
  and exits with success/failure for replay checks.

All thresholds in this package are unverified until real sensor logs are
available. The default launch keeps health checks in contract mode and only
reports observed input state.

Replay contract examples:

```bash
ros2 launch rice_weeding_bringup phase3_localization_replay.launch.py scenario:=nominal
ros2 launch rice_weeding_bringup phase3_localization_replay.launch.py scenario:=no_fix
ros2 launch rice_weeding_bringup phase3_localization_replay.launch.py scenario:=left_no_fix
ros2 launch rice_weeding_bringup phase3_localization_replay.launch.py scenario:=right_no_fix
ros2 launch rice_weeding_bringup phase3_localization_replay.launch.py scenario:=high_covariance
ros2 launch rice_weeding_bringup phase3_localization_replay.launch.py scenario:=stale
ros2 launch rice_weeding_bringup phase3_localization_replay.launch.py scenario:=jump
```

These commands do not start Gazebo, Nav2 or real hardware.

In a second terminal, an expected reason can be checked automatically:

```bash
ros2 run rice_weeding_localization localization_status_expect.py --ros-args \
  -p expected_reason:=position_jump_detected
```
