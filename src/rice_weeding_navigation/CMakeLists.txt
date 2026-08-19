cmake_minimum_required(VERSION 3.8)
project(rice_weeding_navigation)
find_package(ament_cmake REQUIRED)
install(DIRECTORY behavior_trees config launch DESTINATION share/${PROJECT_NAME})
install(PROGRAMS
  scripts/nav2_command_adapter.py
  scripts/paddy_navigation_map.py
  DESTINATION lib/${PROJECT_NAME}
)
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()
ament_package()
