#include "indicators.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace pios_algo::indicators {

std::vector<double> vwap_series(std::span<const double> high, std::span<const double> low,
                                std::span<const double> close, std::span<const double> volume) {
    const std::size_t n = close.size();
    if (high.size() != n || low.size() != n || volume.size() != n) {
        throw std::invalid_argument("vwap_series: input lengths differ");
    }
    std::vector<double> out;
    out.reserve(n);
    double pv = 0.0;
    double vol = 0.0;
    for (std::size_t i = 0; i < n; ++i) {
        const double tp = (high[i] + low[i] + close[i]) / 3.0;
        pv += tp * volume[i];
        vol += volume[i];
        out.push_back(vol != 0.0 ? pv / vol : close[i]);
    }
    return out;
}

double atr(std::span<const double> high, std::span<const double> low, std::span<const double> close,
           std::size_t start) {
    const std::size_t n = close.size();
    if (high.size() != n || low.size() != n) {
        throw std::invalid_argument("atr: input lengths differ");
    }
    if (n < 2) {
        throw std::invalid_argument("atr needs at least 2 bars");
    }
    const std::size_t n_tr = n - 1;
    if (start >= n_tr) {
        throw std::invalid_argument("atr window is empty");
    }
    // Neumaier summation, the same algorithm as CPython's sum() for floats (3.12+).
    double sum = 0.0;
    double comp = 0.0;
    for (std::size_t i = start; i < n_tr; ++i) {
        const double h = high[i + 1];
        const double l = low[i + 1];
        const double prev_c = close[i];
        const double tr = std::max({h - l, std::abs(h - prev_c), std::abs(l - prev_c)});
        const double t = sum + tr;
        if (std::abs(sum) >= std::abs(tr)) {
            comp += (sum - t) + tr;
        } else {
            comp += (tr - t) + sum;
        }
        sum = t;
    }
    if (comp != 0.0 && std::isfinite(comp)) {
        sum += comp;
    }
    return sum / static_cast<double>(n_tr - start);
}

std::pair<double, double> low_high(std::span<const double> low, std::span<const double> high) {
    if (low.size() != high.size()) {
        throw std::invalid_argument("low_high: input lengths differ");
    }
    if (low.empty()) {
        throw std::invalid_argument("low_high: empty window");
    }
    return {*std::min_element(low.begin(), low.end()), *std::max_element(high.begin(), high.end())};
}

}  // namespace pios_algo::indicators
