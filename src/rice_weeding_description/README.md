# rice_weeding_description

从安装态 platform profile 读取车辆尺寸并展开 Xacro，发布
`base_footprint -> base_link -> sensors` 固定 TF。

本包不得发布 `map -> odom` 或 `odom -> base_footprint`。笼式轮当前仅作为外形可视化，动态
关节和驱动插件属于后续仿真底盘模块。

```bash
ros2 launch rice_weeding_description description.launch.py
```
