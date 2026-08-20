# rice_weeding_localization

Phase 3 localization interface package.

This package defines the future localization health boundary for dual GNSS,
IMU, wheel odometry and fused odometry. It does not connect real devices,
does not implement a fusion filter and does not publish TF.

Current executable:

- `localization_health_monitor.py`: subscribes to the planned localization
  inputs and publishes `/rice_weeding/localization/status`.

All thresholds in this package are unverified until real sensor logs are
available. The default launch keeps health checks in contract mode and only
reports observed input state.
