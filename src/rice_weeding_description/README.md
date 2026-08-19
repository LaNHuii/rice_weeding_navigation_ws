# rice_weeding_description

从安装态 platform profile 读取车辆尺寸并展开 Xacro，发布
`base_footprint -> base_link -> sensors` 固定 TF。

本包不得发布 `map -> odom` 或 `odom -> base_footprint`。四个笼式轮使用 simulation-only
连续关节，并携带Gazebo内部DiffDrive与关节状态插件；ROS速度入口和Gazebo内部里程计均
不在本包桥接，车辆仍由bringup的motion-disabled门禁锁定。

```bash
ros2 launch rice_weeding_description description.launch.py
```
