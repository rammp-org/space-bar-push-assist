# Push-assist handle firmware: Waveshare ESP32-P4-WIFI6-POE-ETH reading one load
# cell per handle through two SparkFun HX711 breakouts.
cmake_minimum_required(VERSION 3.20)

# Must be set before project.cmake so IDF picks it up (espp's standard).
set(CMAKE_CXX_STANDARD 23)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)

# rammp-rtps (submodule): the shared RTPS message definitions, HandleForce among them.
if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/external/rammp-rtps/components/rammp_rtps_messages")
  set(EXTRA_COMPONENT_DIRS "${CMAKE_CURRENT_LIST_DIR}/external/rammp-rtps/components/rammp_rtps_messages")
else()
  message(FATAL_ERROR "Missing external/rammp-rtps. Run: git submodule update --init --recursive")
endif()

# Every espp / esp-idf-lib dependency comes from the component registry (see
# main/idf_component.yml); main's REQUIRES pull them in transitively. The
# message definitions come from the rammp-rtps submodule (above).
set(
  COMPONENTS
  "main esptool_py"
  CACHE STRING
  "List of components to include"
  )

project(push_assist)
