# 架构总览

## 第一阶段目标

建立可独立构建的 ROS 2 Humble 工作空间，并固定稻田场景、车辆几何、TF、topic 和仿真边界。
静态合同测试与 Gazebo 动态验收分别记录，不以 SDF 静态检查替代仿真证据。
2026-08-17 已完成稻田世界与 `/clock` 桥接的动态启动验证。

## 目标数据链

```text
paddy_field.sdf
      |
      v
Gazebo Sim ---- /clock
      |
      +---- model pose ---- truth adapter ---- ground_truth
      |                           |
      |                           +---- map -> odom
      |
      +---- base motion ----- odom -> base_footprint
                                |
robot_state_publisher ----------+---- base_link -> sensors
                                |
                                v
                       Nav2 controller boundary
```

同一时刻每条 TF edge 只能有一个发布者。Phase 1 不启动 RTK 融合，因此不存在第二个
`map -> odom` 发布者。

## 坐标系

- `map`：原点位于田块外边界左下（西南）角，x 沿 `20 m` 长边正向，y 沿 `15 m`
  短边正向，z 向上。因此边界坐标范围为 `[0, 20] × [0, 15] m`。
- Gazebo world：为保留现有场景资产仍以田块中心为原点；真值适配器根据 environment
  profile 的边界尺寸派生 `(10.0, 7.5) m` 平移，不在第二处复制场景尺寸。
- `odom`：连续局部里程计坐标系。
- `base_footprint`：机器人在泥面参考平面上的二维投影。
- `base_link`：主体几何中心参考。
- `imu_link`、`gnss_left_link`、`gnss_right_link`、`lidar_link`、`front_camera_link`：固定传感器坐标系。

## 分层

1. 描述层：车辆几何和固定 TF。
2. 仿真层：稻田世界、真值和传感器替身。
3. 导航层：Nav2 地图、规划、控制和行为树边界。
4. Bringup 层：依赖预检和单一进程树组合。

## 安全边界

- 稻苗与杂草不会默认进入普通障碍层。
- 仿真世界中的稻苗采用 visual-only 表达，压苗通过专用几何指标评估。
- 稻苗按 environment profile 的行距、株距和单株几何逐株生成，不使用连续长条视觉替身。
- 全宽作物使用断开的单株几何合并网格渲染，降低 Gazebo visual 数量；
  泥面、浅水和四条田埂的尺寸均从 environment profile 生成。
- 当前视觉验收场景为 `20 m × 15 m`，面积是原 `30 m × 20 m` 的一半；
  可见田埂是单一连续矩形环形网格，四向碰撞体隐藏，泥面和浅水限定在内轮廓。
- 应用用户要求的全内区作物覆盖后当前无可用 headland，所以该场景仅用于视觉与
  场景验收，motion 必须保持 disabled。
- Phase 1 启动入口不连接 CAN、底盘驱动或真实 `/cmd_vel`。
- 缺少 Gazebo/桥接依赖时启动必须失败并给出缺失包名。

## 后续阶段

- Phase 2：Gazebo 差速运动、打滑扰动与 Nav2 真值闭环。
- Phase 3：双天线 RTK、IMU、轮速融合和定位质量门禁。
- Phase 4：稻行视觉偏差与作物/障碍语义分层。
- Phase 5：覆盖规划、地头掉头、路径验证和仿真执行。
- Phase 6：杂草检测坐标变换与除草触发接口。

## Phase 2 当前门禁

Phase 2 使用 `phase2_simulation.launch.py` 作为独立入口。它复用 Phase 1 稻田世界和
`robot_description`，延时调用 `ros_gz_sim create` 生成 `rice_weeding_robot` 实体。

```text
paddy_field.sdf + robot_description
                 |
                 v
          rice_weeding_robot (Gazebo entity)
```

机器人实体生成门禁已通过。当前真值门禁把 Gazebo world 的动态模型世界位姿桥接到只在
仿真入口运行的真值适配器，并筛选 `rice_weeding_robot`。适配器发布
`/rice_weeding/simulation/ground_truth`。`odom` 与 Gazebo world 初始对齐，`map` 原点位于
外边界左下角，因此适配器唯一发布平移为 `(10.0, 7.5, 0) m` 的 `map -> odom`。

该门禁仍不发布 `odom -> base_footprint` 或 Nav2 使用的定位里程计；它们归下一步仿真
底盘里程计所有。当前场景无 headland，所以 `motion_enabled` 仍必须为 `false`。
