cmake_minimum_required(VERSION 3.8)
project(rice_weeding_simulation)
find_package(ament_cmake REQUIRED)
install(DIRECTORY config launch meshes worlds DESTINATION share/${PROJECT_NAME})
install(FILES ../../profiles/environments/paddy_field.yaml DESTINATION share/${PROJECT_NAME}/profiles/environments)
install(PROGRAMS
  scripts/simulation_chassis_odometry.py
  scripts/simulation_truth_adapter.py
  DESTINATION lib/${PROJECT_NAME})
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()
ament_package()
