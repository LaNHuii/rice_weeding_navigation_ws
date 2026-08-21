cmake_minimum_required(VERSION 3.8)
project(rice_weeding_localization)

find_package(ament_cmake REQUIRED)

install(PROGRAMS
  scripts/localization_health_logic.py
  scripts/localization_health_monitor.py
  scripts/localization_replay_sample_publisher.py
  scripts/localization_status_expect.py
  DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY config launch DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
