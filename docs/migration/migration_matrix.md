# 迁移矩阵

更新时间：2026-08-18。

状态定义：`SKELETON` 仅证明目录和合同存在；`BUILT` 证明 ROS 包构建；`SIMULATED` 证明动态
仿真；`FIELD_VALIDATED` 证明实地验收。低级状态不能替代高级状态。

| 模块/数据链 | 当前状态 | 当前证据 | 下一门禁 |
| --- | --- | --- | --- |
| 工作空间与合同 | BUILT | 4个包被 colcon 发现并构建；根合同测试 `12 passed` | 继续按模块补充动态合同 |
| 车辆描述 | SIMULATED | canonical profile、Xacro/URDF 树和安装态发布通过；Phase 2 动态生成 `rice_weeding_robot` 实体并截图验收 | 实车尺寸复测与仿真轮组运动关节 |
| 稻田场景 | SIMULATED | 面积缩至 `20 m × 15 m = 300 m²`；12,936 株绿色作物覆盖全部内区；田埂为单一连续矩形外框，泥面与浅水不超界 | 机器人实体生成前保持 motion disabled |
| 仿真真值定位 | SIMULATED | Gazebo world 中心 `(0,0,0.05)` 转换为 map `(10,7.5,0.05)`；`map -> odom` 实测平移 `(10,7.5,0)`；时间戳与单发布者验证通过 | 仿真底盘里程计闭合 `odom -> base_footprint` |
| 仿真底盘运动 | NOT_STARTED | 仅定义接口 | 笼式轮差速替身、打滑模型和停止测试 |
| Nav2 真值闭环 | NOT_STARTED | 包/接口边界 | 定点导航、障碍停车、越界拒绝测试 |
| RTK/IMU 融合 | NOT_STARTED | 架构占位 | 单独 Phase 3 设计与回放数据 |
| 稻行/杂草视觉 | NOT_STARTED | 语义接口占位 | 单独定义数据集、标注和指标 |
| 覆盖规划 | NOT_STARTED | `0.75 m` 作业带为仿真假设 | 明确除草机构宽度后再接规划器 |

Phase 2 的“机器人实体生成”和“仿真真值定位”门禁均已通过。仿真底盘里程计和 Nav2
状态不因实体可见或真值话题存在而提前升级。真值适配器不发布
`odom -> base_footprint`，下一门禁仍由仿真底盘唯一拥有该 edge。

本机已可调用 `ros_gz_sim` 与 `ros_gz_bridge`。2026-08-17 限时动态验收中，Gazebo
连续运行至 SIGINT 停止，`/clock` 返回 `1360.822 s`，ROS 图中无 `/cmd_vel`。
