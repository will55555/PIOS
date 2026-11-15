// Python binding for the indicator library (pybind11). No policy, no state.
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <vector>

#include "indicators.hpp"

namespace py = pybind11;
namespace ind = pios_algo::indicators;

PYBIND11_MODULE(pios_algo_compute, m) {
    m.doc() = "pios-algo C++ compute (ADR-PIOS-ALGO-009). Computes only; Python decides.";
    m.def(
        "vwap_series",
        [](const std::vector<double>& high, const std::vector<double>& low, const std::vector<double>& close,
           const std::vector<double>& volume) { return ind::vwap_series(high, low, close, volume); },
        py::arg("high"), py::arg("low"), py::arg("close"), py::arg("volume"));
    m.def(
        "atr",
        [](const std::vector<double>& high, const std::vector<double>& low, const std::vector<double>& close,
           std::size_t start) { return ind::atr(high, low, close, start); },
        py::arg("high"), py::arg("low"), py::arg("close"), py::arg("start"));
    m.def(
        "low_high",
        [](const std::vector<double>& low, const std::vector<double>& high) { return ind::low_high(low, high); },
        py::arg("low"), py::arg("high"));
}
