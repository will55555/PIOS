# C++ compute for pios-algo (ADR-PIOS-ALGO-009, amended 2026-11-14).
# C++ computes, Python decides: nothing here owns policy, authorization,
# broker connectivity, order state, risk decisions or financial truth.
cmake_minimum_required(VERSION 3.28)
project(pios_algo_compute LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Bit-for-bit parity with the Python reference: no fused multiply-add, no fast-math.
if(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
  add_compile_options(/fp:precise)
elseif(MSVC)  # clang-cl
  add_compile_options(/fp:precise /clang:-ffp-contract=off)
else()  # GCC, Clang
  add_compile_options(-ffp-contract=off -fno-fast-math)
endif()

# indicators/  indicator library shared by backtests and the live engine
add_library(pios_algo_indicators STATIC indicators/indicators.cpp)
target_include_directories(pios_algo_indicators PUBLIC indicators)

# Python module. Required when pip/uv builds the package; optional for a plain cmake build.
set(PYBIND11_FINDPYTHON ON)
if(SKBUILD)
  find_package(pybind11 CONFIG REQUIRED)
else()
  find_package(pybind11 CONFIG QUIET)
endif()
if(pybind11_FOUND)
  pybind11_add_module(pios_algo_compute python/module.cpp)
  target_link_libraries(pios_algo_compute PRIVATE pios_algo_indicators)
  install(TARGETS pios_algo_compute LIBRARY DESTINATION .)
endif()

# Still to come, one target each: backtest/, scanner/, montecarlo/, options/ (QuantLib), orderbook/
