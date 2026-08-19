# rice_weeding_simulation

当前世界表达20 m × 15 m单一连续矩形田埂外框、边界内的浅水与泥面，以及按30 cm
行株距逐株表达的绿色稻苗。沿稻行两端各保留2.50 m地头；作物网格离散后实际无苗宽度
约2.64 m，可用于低速掉头。
稻苗没有刚性碰撞。四个轮子已使用 simulation-only 连续关节和 Gazebo 内部 DiffDrive
替身；非零运动、打滑和传感器噪声仍属于后续门禁。

Phase 2 入口另提供两个 simulation-only 适配器：真值适配器唯一发布 `map -> odom`，
底盘里程计适配器唯一发布 `odom -> base_footprint` 和定位 Odometry。两者均不在实车入口
启用。轮关节状态单向桥接到 `/joint_states`，但内部差速命令和插件里程计均不桥接 ROS，
默认启动时软件安全门禁提供保持为零的 `/rice_weeding/safety/cmd_vel`。显式
`motion_enabled:=true` 并通过 profile 地头检查后，它才单向桥接到 Gazebo 内部命令；
原始命令不能直接驱动车辆。

```bash
ros2 launch rice_weeding_simulation paddy_world.launch.py
```
