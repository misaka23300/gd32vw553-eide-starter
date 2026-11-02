# RISC-V toolchain for the GD32VW553 bare-metal project
#
# 用法（由 CMakePresets.json 自动传入）：
#   cmake -DCMAKE_TOOLCHAIN_FILE=cmake/riscv-toolchain.cmake ..
#
# 编译器查找顺序：
#   1) -DMOS8_GCC_DIR=<dir>（该目录下要有 riscv-nuclei-elf-gcc）
#   2) 工作区自带的 home/tools/gcc/bin
#   3) PATH

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR riscv)

set(_candidate_dirs "")
if (DEFINED MOS8_GCC_DIR AND MOS8_GCC_DIR)
    list(APPEND _candidate_dirs "${MOS8_GCC_DIR}")
endif ()
# 本文件位于 <project>/cmake/，上三级是工作区的 home 目录
get_filename_component(_home "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
list(APPEND _candidate_dirs "${_home}/tools/gcc/bin")

set(_gcc "")
foreach (_dir ${_candidate_dirs})
    if (EXISTS "${_dir}/riscv-nuclei-elf-gcc.exe")
        set(_gcc "${_dir}/riscv-nuclei-elf-gcc.exe")
        break()
    elseif (EXISTS "${_dir}/riscv-nuclei-elf-gcc")
        set(_gcc "${_dir}/riscv-nuclei-elf-gcc")
        break()
    endif ()
endforeach ()

if (_gcc STREQUAL "")
    find_program(_gcc riscv-nuclei-elf-gcc)
    if (_gcc STREQUAL "_gcc-NOTFOUND" OR _gcc STREQUAL "")
        message(FATAL_ERROR "riscv-nuclei-elf-gcc not found; set -DMOS8_GCC_DIR=<toolchain bin dir>")
    endif ()
endif ()

get_filename_component(_bin "${_gcc}" DIRECTORY)
message(STATUS "RISC-V GCC: ${_gcc}")

set(CMAKE_C_COMPILER   "${_gcc}")
set(CMAKE_ASM_COMPILER "${_gcc}")
set(CMAKE_CXX_COMPILER "${_bin}/riscv-nuclei-elf-g++")
set(CMAKE_AR           "${_bin}/riscv-nuclei-elf-ar")
set(CMAKE_RANLIB       "${_bin}/riscv-nuclei-elf-ranlib")
set(CMAKE_OBJCOPY      "${_bin}/riscv-nuclei-elf-objcopy")
set(CMAKE_OBJDUMP      "${_bin}/riscv-nuclei-elf-objdump")
set(CMAKE_SIZE         "${_bin}/riscv-nuclei-elf-size")

set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
set(CMAKE_EXECUTABLE_SUFFIX ".elf")
