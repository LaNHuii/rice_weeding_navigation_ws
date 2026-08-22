# AGENTS.md

## Scope


- 本仓库用于稻田除草机器人自主导航与仿真。
- 当前阶段只推进“稻田场景 -> 仿真真值 -> Nav2 接口”这一条数据链。
- 只创建架构文档、包骨架、接口桩、场景资产、测试和依赖清单。
- 不迁移第三方算法源码，不接入真实底盘运动。

## Hard rules

- 一次只迁移一个模块或一条数据链。
- 禁止硬编码用户名、工作空间路径、设备路径、地图路径和 RTK 基站地址。
- `profiles/platforms/rice_weeding_prototype.yaml` 是车辆几何唯一真源。
- `profiles/environments/paddy_field.yaml` 是第一版稻田场景参数唯一真源。
- 未验证参数必须显式标为 `verified: false` 或 `simulation_only: true`。
- 架构或接口变化必须同时更新 `docs/`、本文件和
  `docs/migration/migration_matrix.md`。
- 不允许多个节点发布同一 TF edge。
- 不得把稻苗点云无条件写入 Nav2 障碍层；稻苗、杂草和真实障碍必须分层表达。
- 仿真真值 TF 只能在仿真入口中启用，真实系统不得复用真值发布者。
- 仿真入口默认 motion disabled；在速度链、安全门禁和停止测试完成前不得自动运动。

## TF ownership

- `map -> odom`：Phase 1 仅由仿真真值定位发布；未来实车由全局融合定位唯一发布。
- `odom -> base_footprint`：Phase 1 仅由仿真底盘发布；未来实车由连续里程计唯一发布。
- `base_footprint -> base_link -> sensor`：仅由机器人描述发布固定 TF。

## Geometry and crop-row contract

- 主体外廓为用户确认的 `1.0 m x 1.0 m x 0.30 m`。
- 导航 footprint 必须从 platform profile 消费，不得在 Nav2、覆盖规划或仿真中复制第二份。
- `0.75 m` 轮距、`0.16 m` 净空、笼式轮尺寸与质量均为仿真假设，实车使用前必须测量。
- 作物网格的 canonical 行距和株距均为 `0.15 m`。
- Gazebo 作物必须逐株表达，不得使用连续长条代替；单株仿真几何只从
  environment profile 消费。
- 田埂可见几何必须是单一连续矩形外框，不得使用会在田块内相交的长条。
- 作物区禁止原地转向；掉头必须发生在显式 headland 中。
- 当前“全边界内覆盖”场景没有可用 headland，因此必须继续保持 motion disabled；
  启用任何转向或路径执行前必须重建显式 headland。
- 稻苗是作物语义，不是默认障碍物；人员、田埂、沟渠、石块和农具才进入安全障碍链。

## Phase 1 non-goals

- RTK/IMU/轮速融合实现。
- 稻行或杂草视觉算法。
- 覆盖路径执行、除草机构控制和实车速度输出。
- 水体流体动力学、泥土有限元或高保真植株接触仿真。
- 复制 FAST-LIVO2、Nav2、OpenNav、Fields2Cover 或其他第三方源码。

## Phase 2 current gate

- Phase 1 的文档、启动入口和验收证据必须保留，Phase 2 使用独立入口迭代。
- 当前只允许在 Gazebo 中生成机器人实体，初始位姿从 environment profile 消费。
- 当前不启用差速驱动、`/cmd_vel`、`odom -> base_footprint` 或 `map -> odom`。
- 仿真真值定位、速度链、安全门禁与停止测试必须各自通过后才能解锁运动。

## Phase 3 planning boundary

- Phase 3 当前只允许定义双天线 GNSS、IMU、轮速、融合定位和定位健康状态的接口、文档、
  包骨架与可回放测试合同；不得接入真实设备、RTK 基站、滤波器实现或实车速度输出。
- `rice_weeding_localization` 当前只能作为 Phase 3 接口桩与健康状态合同包；默认不得发布
  `map -> odom`、`odom -> base_footprint` 或假的融合 Odometry。
- Phase 3 replay 样例只能发布 simulation-only 输入消息，用于合同验证；不得伪装成真实
  传感器驱动、RTK 固定解或实车融合定位。
- Phase 3 状态自检工具只能订阅 `/rice_weeding/localization/status`，不得发布定位、TF
  或速度输出。
- Phase 3 外参合同可记录仿真 profile 派生值，但必须标为未验证；真实 rosbag 规范不得把
  仿真真值当作实车参考输入。

## Phase 4 semantic boundary

- Phase 4 当前只允许定义稻田语义地图 schema、示例文件、无 Qt 数据工具、静态合同测试和
  一个只读 RViz Marker 预览节点。
- `crop_row` 与 `weed_patch` 不得默认写入 Nav2 障碍层；`hard_obstacle`、
  `negative_obstacle` 和 `keepout_zone` 才能进入后续安全/禁行 mask 合同。
- 参考工程工具若要直接迁移，必须是独立、即插即用模块；当前 `rice_weeding_semantics`
  是稻田版自写工具，只参考 AGT 语义数据合同思路。
- Phase 4 纯数据 keepout mask 只能由 `hard_obstacle`、`negative_obstacle` 和
  `keepout_zone` 生成；不得从 `crop_row` 或 `weed_patch` 生成默认障碍。
- Phase 4 离线生成器只能从显式传入的 environment profile 生成 simulation-only GeoJSON；
  不得硬编码工作空间路径或伪装成实车语义标注。
- Phase 4 离线 keepout mask 导出器只能生成 simulation-only 文件工件；不得启动 Nav2
  KeepoutFilter、发布 ROS `OccupancyGrid` 或伪装成在线语义地图 server。
- Phase 4 允许一个显式门禁保护的 simulation-only keepout mask 发布器；它只能读取显式传入的
  GeoJSON，且必须要求用户确认 simulation-only，发布 `/rice_weeding/semantics/keepout_mask`。
  它不得启动 Nav2 KeepoutFilter、发布 TF、速度、Odometry 或实车控制。
- Phase 4 允许一个只读 RViz Marker 预览节点，它只能读取显式传入的 GeoJSON 并发布
  `/rice_weeding/semantics/markers`；不得发布 TF、速度、Odometry、keepout mask 或 Nav2
  costmap。
- 当前不得迁移 Qt 编辑器、语义地图 server、Nav2 KeepoutFilter 总控或覆盖规划代码。
- 未来实车 `map -> odom` 只可由唯一融合定位节点发布；未来实车
  `odom -> base_footprint` 只可由唯一连续里程计节点发布。仿真真值与仿真底盘节点不得复用。
- 定位健康语义至少包含 Fix、位置/偏航协方差、数据时效与位置跳变。未取得实测数据前，
  健康阈值必须标为未验证，不得硬编码为实车安全结论。
