cmake_minimum_required(VERSION 3.28)

project(swisseph LANGUAGES C)

set(SWISSEPH_SOURCES
    swedate.c
    swehouse.c
    swejpl.c
    swemmoon.c
    swemplan.c
    sweph.c
    swephlib.c
    swecl.c
    swehel.c
)

add_library(swisseph STATIC ${SWISSEPH_SOURCES})
target_include_directories(swisseph PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_features(swisseph PRIVATE c_std_99)
if(NOT MSVC)
    target_compile_options(swisseph PRIVATE -fPIC)
endif()
if(UNIX)
    target_link_libraries(swisseph PUBLIC m)
endif()

set_target_properties(swisseph PROPERTIES
    OUTPUT_NAME swe
    POSITION_INDEPENDENT_CODE ON
)
