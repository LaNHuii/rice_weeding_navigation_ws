# 迁移矩阵

更新时间：2026-08-20。

状态定义：`SKELETON` 仅证明目录和合同存在；`BUILT` 证明 ROS 包构建；`SIMULATED` 证明动态
仿真；`FIELD_VALIDATED` 证明实地验收。低级状态不能替代高级状态。

| 模块/数据链 | 当前状态 | 当前证据 | 下一门禁 |
| --- | --- | --- | --- |
| 工作空间与合同 | BUILT | 7个包被 colcon 发现并构建；根合同测试覆盖 Phase 1/2/3/4 静态边界 | 继续按模块补充动态合同 |
| 车辆描述 | SIMULATED | canonical profile、Xacro/URDF 树和安装态发布通过；Phase 2 动态生成 `rice_weeding_robot` 实体并截图验收 | 实车尺寸复测与仿真轮组运动关节 |
| 稻田场景 | SIMULATED | `20 m × 15 m = 300 m²`；2,401 株绿色作物按 `0.30 m` 网格排列；两端各有 `2.50 m` 地头，田埂为单一连续矩形外框 | Nav2 可通行空间与边界拒绝验证 |
| 仿真真值定位 | SIMULATED | Gazebo world 中心 `(0,0,0.05)` 转换为 map `(10,7.5,0.05)`；`map -> odom` 实测平移 `(10,7.5,0)`；时间戳与单发布者验证通过 | 仿真底盘里程计闭合 `odom -> base_footprint` |
| 仿真底盘里程计 | SIMULATED | 注入 odom `(1,2,0.05)` 后 Odometry一致且单发布者；`map -> base_link=(11,9.5,0.28)`；完整TF闭合；Twist为零 | 差速驱动替身与零速度不漂移测试 |
| 仿真差速底盘替身 | SIMULATED | 无界面生成实体；`/joint_states` 含四轮；安全速度单向桥接 DiffDrive | Nav2 控制器接入 |
| 软件速度安全门禁 | SIMULATED | 默认禁用、限幅、超时归零；唯一安全输出已桥接仿真 DiffDrive | Nav2 输出经安全门禁 |
| 仿真底盘实际运动 | SIMULATED | 东侧地头内完成 `90° → 0.64 m 横移 → 90°` 掉头；最终朝向约 `179.4°`，timeout 后 odom Twist 为零 | Nav2 定点导航、田埂边界拒绝 |
| Nav2 真值闭环 | BUILT | profile 驱动 `/map`、forward-only 行为树、无状态命令适配器和安全门禁已接入；生命周期与 action 动态启动通过 | 动态定点到达、停车、田埂外目标拒绝 |
| RTK/IMU/轮速融合接口 | SKELETON | `rice_weeding_localization` 包、健康监视器、7类 simulation-only replay 样例、状态自检工具、外参合同和 rosbag 记录规范；可验证 Fix、协方差、时效、跳变；无驱动、无滤波器、无实测 | 真实 rosbag 样本和实测外参 |
| 稻田语义地图 | SKELETON | `rice_weeding_semantics` 包、稻田 GeoJSON schema、示例语义地图和无 ROS/Qt 校验工具；未迁移 Qt/server/Nav2 keepout | 语义地图 server 与 RViz Marker |
| 稻行/杂草视觉 | NOT_STARTED | 语义接口占位 | 单独定义数据集、标注和指标 |
| 覆盖规划 | NOT_STARTED | `0.75 m` 作业带为仿真假设 | 明确除草机构宽度后再接规划器 |

Phase 2 的“机器人实体生成”“仿真真值定位”“仿真底盘里程计”“仿真差速底盘替身”和
“软件速度安全门禁”均已通过。仿真底盘实际运动和 Nav2 状态不因此提前升级。真值适配器不发布
`odom -> base_footprint`，该 edge 由独立仿真底盘里程计唯一拥有。

本机已可调用 `ros_gz_sim` 与 `ros_gz_bridge`。2026-08-17 限时动态验收中，Gazebo
连续运行至 SIGINT 停止，`/clock` 返回 `1360.822 s`，ROS 图中无 `/cmd_vel`。
