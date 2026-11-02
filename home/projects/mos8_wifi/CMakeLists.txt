# GD32VW553 8-channel MOSFET controller — CMake build
#
#   cmake --preset default        # 配置
#   cmake --build --preset default
#
# 产物与 Makefile 完全一致（便于 gd32.py flash 直接使用）：
#   build/mos8_wifi.elf / .bin / .hex / .map

cmake_minimum_required(VERSION 3.20)

project(mos8_wifi LANGUAGES C ASM)

# 工程位于 <workspace>/home/projects/mos8_wifi，上两级是 home
get_filename_component(HOME_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
set(SDK_DIR "${HOME_DIR}/sdk/GD32VW55x_Firmware_Library")

if (NOT EXISTS "${SDK_DIR}/Firmware/GD32VW55x_standard_peripheral/gd32vw55x.h")
    message(FATAL_ERROR "GD32VW55x firmware library not found at ${SDK_DIR}")
endif ()

set(ARCH_FLAGS -march=rv32imafdc -mabi=ilp32d)
set(OUT_DIR "${CMAKE_CURRENT_SOURCE_DIR}/build")

# ---------------------------------------------------------------- sources

set(APP_SRCS
    src/main.c
    src/board.c
    src/mosfet.c
    src/led.c
    src/console.c
    src/wifi_link.c
    src/systick.c
    src/gd32vw55x_it.c
    src/retarget.c
)

file(GLOB SDK_ENV_SRCS "${SDK_DIR}/Firmware/RISCV/env_Eclipse/*.c")
file(GLOB SDK_STUB_SRCS "${SDK_DIR}/Firmware/RISCV/stubs/*.c")
list(FILTER SDK_STUB_SRCS EXCLUDE REGEX "/write\\.c$")
file(GLOB SDK_PERIPH_SRCS "${SDK_DIR}/Firmware/GD32VW55x_standard_peripheral/Source/*.c")

set(SDK_SRCS
    ${SDK_ENV_SRCS}
    ${SDK_STUB_SRCS}
    ${SDK_PERIPH_SRCS}
    "${SDK_DIR}/Firmware/GD32VW55x_standard_peripheral/system_gd32vw55x.c"
)

set(ASM_SRCS
    "${SDK_DIR}/Firmware/RISCV/env_Eclipse/start.S"
    "${SDK_DIR}/Firmware/RISCV/env_Eclipse/entry.S"
)

add_executable(${PROJECT_NAME} ${APP_SRCS} ${SDK_SRCS} ${ASM_SRCS})

# ---------------------------------------------------------------- flags

target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${SDK_DIR}/Firmware/GD32VW55x_standard_peripheral
    ${SDK_DIR}/Firmware/GD32VW55x_standard_peripheral/Include
    ${SDK_DIR}/Firmware/RISCV/drivers
    ${SDK_DIR}/Firmware/RISCV/stubs
)

target_compile_options(${PROJECT_NAME} PRIVATE
    ${ARCH_FLAGS}
    -std=gnu11
    -O2
    -g
    -Wall
    -ffunction-sections
    -fdata-sections
)

target_compile_definitions(${PROJECT_NAME} PRIVATE USE_STDPERIPH_DRIVER)

set(LDSCRIPT "${SDK_DIR}/Firmware/RISCV/env_Eclipse/GD32VW553xM.lds")

target_link_options(${PROJECT_NAME} PRIVATE
    ${ARCH_FLAGS}
    -T${LDSCRIPT}
    -nostartfiles
    -Wl,--gc-sections
    -Wl,-Map=${OUT_DIR}/${PROJECT_NAME}.map
)

target_link_libraries(${PROJECT_NAME} PRIVATE m c gcc)

# 与 Makefile 输出同一位置，方便 gd32.py flash 直接找到
set_target_properties(${PROJECT_NAME} PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${OUT_DIR}"
    OUTPUT_NAME "${PROJECT_NAME}"
    SUFFIX ".elf"
)

add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary "$<TARGET_FILE:${PROJECT_NAME}>" "${OUT_DIR}/${PROJECT_NAME}.bin"
    COMMAND ${CMAKE_OBJCOPY} -O ihex   "$<TARGET_FILE:${PROJECT_NAME}>" "${OUT_DIR}/${PROJECT_NAME}.hex"
    COMMENT "objcopy -> ${PROJECT_NAME}.bin/.hex"
)

add_custom_target(size
    COMMAND ${CMAKE_SIZE} "$<TARGET_FILE:${PROJECT_NAME}>"
    DEPENDS ${PROJECT_NAME}
    COMMENT "firmware size"
)
