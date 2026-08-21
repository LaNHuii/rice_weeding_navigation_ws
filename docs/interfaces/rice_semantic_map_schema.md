# 稻田语义地图合同 1.0

Phase 4 使用独立 GeoJSON 语义文件表达稻田对象。基础 `/map` OccupancyGrid 保持只读；
不得把稻苗、杂草或禁行语义永久写入源 PGM。

本阶段参考了 `agt_navigation_v2-main` 的无 GUI 语义数据工具思路，但当前没有直接迁移参考工程
工具。直接迁移只适用于后续发现的独立、即插即用模块；本轮新增的是稻田版自写数据工具，主要
参考以下设计模式：

- `semantic_model`：GeoJSON FeatureCollection 数据模型。
- `semantic_io`：语义文件原子读写。
- `semantic_validation`：稳定错误码和合同校验。

未迁移 Qt 编辑器、AGT semantic map server、Nav2 KeepoutFilter 总控和覆盖规划代码。

## 坐标合同

- 所有几何使用 `frame_id: map`。
- 坐标为米制 `[x, y]`，不是经纬度、图像像素或栅格索引。
- Polygon 外环必须闭合。
- Feature ID 必须是小写 `snake_case`。

## Feature 类型

| feature_type | Geometry | 含义 | 是否默认进入障碍层 |
| --- | --- | --- | --- |
| `field_boundary` | Polygon | 稻田外边界 | 否 |
| `crop_row` | LineString | 稻苗行/行中心线，保护对象 | 否 |
| `weed_patch` | Polygon | 杂草目标 | 否 |
| `hard_obstacle` | Polygon | 人、石块、农具、田埂等碰撞风险 | 是，后续安全层 |
| `negative_obstacle` | Polygon | 沟渠、坑洞等负障碍 | 是，后续可通行性层 |
| `headland_zone` | Polygon | 明确掉头区域 | 否 |
| `keepout_zone` | Polygon | 语义禁行区 | 是，后续 keepout mask |
| `work_direction` | LineString | 推荐作业方向 | 否 |

`crop_row` 和 `weed_patch` 必须保持语义对象身份，不能无条件写入 Nav2 普通障碍层。
`hard_obstacle`、`negative_obstacle` 和 `keepout_zone` 必须声明 `safety_layer`。

## 当前实现

`rice_weeding_semantics` 只包含无 ROS、无 Qt 的数据工具和示例文件。它不会发布 TF、速度、
Nav2 costmap 或实车控制命令。后续语义地图 server 必须作为独立门禁实现。

`profile_semantic_builder.py` 可从 `profiles/environments/paddy_field.yaml` 派生
simulation-only 语义图：田块边界、profile 指定的 x 方向两端 headland、作业方向和逐行
`crop_row`。它不推断杂草或真实障碍；这些必须来自后续标注或感知输入。
