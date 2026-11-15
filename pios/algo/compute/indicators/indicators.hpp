// pios-algo indicator library (ADR-PIOS-ALGO-009). Computes only; Python decides.
#pragma once

#include <cstddef>
#include <span>
#include <utility>
#include <vector>

namespace pios_algo::indicators {

// Cumulative VWAP on typical price (h + l + c) / 3. Zero cumulative volume -> close.
std::vector<double> vwap_series(std::span<const double> high, std::span<const double> low,
                                std::span<const double> close, std::span<const double> volume);

// Mean of true ranges tr[start:], tr[k] built from bar k+1 and the close of bar k.
double atr(std::span<const double> high, std::span<const double> low, std::span<const double> close,
           std::size_t start);

// (min low, max high) over a window.
std::pair<double, double> low_high(std::span<const double> low, std::span<const double> high);

}  // namespace pios_algo::indicators
