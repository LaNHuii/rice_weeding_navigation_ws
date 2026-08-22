cmake_minimum_required(VERSION 3.8)
project(rice_weeding_semantics)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  config
  examples
  rice_weeding_semantics
  DESTINATION share/${PROJECT_NAME})
install(PROGRAMS
  scripts/generate_profile_semantic_map.py
  scripts/generate_keepout_mask.py
  scripts/semantic_keepout_mask_publisher.py
  scripts/semantic_marker_preview.py
  DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
