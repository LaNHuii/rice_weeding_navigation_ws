# 最小检查

```bash
source /opt/ros/humble/setup.bash
cd "$RICE_WEEDING_WS"
env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /usr/bin/python3 -m pytest -q tests
colcon list
colcon build --symlink-install
```

静态检查覆盖：

- 用户确认尺寸和 `0.15 m` 作物网格未被漂移修改。
- footprint 只有 platform profile 一份真源。
- Xacro 不发布 `map -> odom` 或 `odom -> base_footprint`。
- SDF 世界使用米制 ENU 约定且稻苗骨架无碰撞。
- 包清单不依赖参考仓库的绝对路径。

已执行的 Gazebo 动态检查（2026-08-17）：

- `/clock` 存在且返回仿真时间（采样值 `1360.822 s`）。
- ROS 节点仅包含时钟桥和机器人状态发布者，话题中无 `/cmd_vel`。
- 在独立 Gazebo transport 分区中截图确认 `crop_field` 新场景生效：12,936 株绿色
  作物覆盖全部内区，田埂为单一连续矩形外框，泥面和浅水无越界。
- Phase 2 入口返回 `OK creation of entity`，Gazebo 实体树和截图均确认
  `rice_weeding_robot` 存在；ROS 话题中仍无 `/cmd_vel`。
- Phase 2 真值入口从 Gazebo world 动态位姿读取机器人实际位置；左下角原点调整后隔离
  动态验证 world `(0, 0, 0.05 m)` 正确转换为 map `(10, 7.5, 0.05 m)`；
  `/rice_weeding/simulation/ground_truth` 发布者数为 1。
- `map -> odom` 动态查询为 `(10, 7.5, 0) m` 平移；ROS 图中仍无 `/cmd_vel` 和
  `/rice_weeding/localization/odometry`。
- 隔离注入仿真时钟 `123.456 s` 与位姿 `(1, 2, 0.05 m)` 后，真值输出保持相同位姿并
  使用 `123.456 s`，证明 Fortress Pose_V 顶层时间戳缺失的适配已生效。

后续动态门禁：

- 下一底盘门禁闭合 `odom -> base_footprint` 后，TF edge 发布者仍唯一。
- 零速度时机器人不漂移。
- 非零速度只经过仿真安全链。
- 机器人不得越过田埂或在种植区原地旋转。
