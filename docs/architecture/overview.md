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
- 当前导航验收场景为 `20 m × 15 m`，面积是原 `30 m × 20 m` 的一半；可见田埂是单一
  连续矩形环形网格，四向碰撞体隐藏，泥面和浅水限定在内轮廓。
- 稻苗行距和株距均为 `0.30 m`；沿稻行的两端各保留 profile 指定的 `2.50 m` headland。
  作物网格离散后实际无苗宽度约 `2.64 m`，用于低速掉头与停车验证。
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

真值门禁自身不发布 `odom -> base_footprint` 或 Nav2 使用的定位里程计；它们归独立仿真
底盘里程计所有。当前场景具备 profile 驱动的两端 headland，仍须显式设置
`motion_enabled:=true` 才能运动。

## Phase 2 仿真底盘里程计门禁

独立 `simulation_chassis_odometry` 节点订阅同一个 Gazebo world 动态模型位姿，但不应用
`map` 左下角偏移，而是在与 Gazebo world 对齐的 `odom` 中发布：

```text
/rice_weeding/simulation/pose_info
                 |
                 v
simulation_chassis_odometry
       |                   |
       v                   v
/rice_weeding/localization/odometry   odom -> base_footprint
```

至此 TF 结构闭合为 `map -> odom -> base_footprint -> base_link -> sensors`。节点是
simulation-only 位姿替身：motion disabled 时 Twist 为零，motion enabled 时从连续 Gazebo
位姿差分得到 Twist；它不代表轮速积分、打滑模型或实车里程计。

## Phase 2 仿真差速底盘替身门禁

四个轮子由固定关节改为 simulation-only 连续关节，质量、惯量替身、阻尼、摩擦、轮距、
轴距和速度限制均从 platform profile 消费。Gazebo 内部 JointStatePublisher 输出轮关节
状态，经单向 bridge 形成 ROS `/joint_states`；内部 DiffDrive 为以后安全速度链保留动力学
入口。

```text
Gazebo wheel joints ---- internal joint state ---- bridge ---- /joint_states

raw navigation command -X-> internal/locked_cmd_vel

safe command ------------> internal/locked_cmd_vel ---- DiffDrive
                                      |
                                      +---- internal odom/TF -X-> ROS
```

`-X->` 表示当前刻意不连接。安全命令唯一接入 DiffDrive，且内部 odometry/TF 保持断开，
避免产生第二个里程计/TF 发布者。默认仍禁止非零速度；只有 profile 的地头检查通过后显式
开启仿真运动。

## Phase 2 软件速度安全门禁

参考项目采用独立安全仲裁层，这一隔离思想适合当前实车迁移；但其 BUNKER 履带参数、
手动优先仲裁和 CAN 接口不适用于当前四轮稻田底盘，因此没有复制。当前实现保持最小链路：

```text
future Nav2 controller
        |
        v
/rice_weeding/navigation/cmd_vel_raw
        |
        v
rice_weeding_safety -- wall-clock timeout / finite / planar / limit checks
        |
        v
/rice_weeding/safety/cmd_vel  --->  Gazebo internal command
                         -X->  real chassis
```

默认 Phase 2 启动强制门禁禁用并持续发布零。只有环境 profile 的地头宽度不少于 platform
profile 要求并显式设置 `motion_enabled:=true` 时，安全输出才桥接到 Gazebo DiffDrive。这个
门禁不替代硬件急停、实车底盘 watchdog 或实车制动距离验证。

## Phase 2 Nav2 定点导航门禁

Phase 2 现在增加一条受限的 Nav2 闭环，且仍只作用于 Gazebo：

```text
environment profile -> static /map (bund occupied, crops free)
                              |
                              v
map -> odom -> base_footprint -> Nav2 planner/controller
                                      |
                                      v
                                 /cmd_vel -> adapter -> cmd_vel_raw
                                      |
                                      v
                               existing safety gate -> Gazebo DiffDrive
```

地图以 profile 的 `map` 西南原点生成，田埂成为静态占用并经 footprint/inflation 形成边界拒绝。
Nav2 footprint 也由启动入口读取平台 profile 后写入临时参数，避免复制几何。稻苗不进入该地图；
这是当前语义合同，不是“稻苗可忽略”的实车安全结论。

当前只配置无 Spin、无 BackUp 的“规划 + 前向跟随”行为树，且关闭 Nav2 原地转向、倒车。因此
验证目标必须位于当前朝向的前方和田埂内；转弯与覆盖行为仍留给后续专门的地头/覆盖门禁。
