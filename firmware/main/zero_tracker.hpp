#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <vector>

/// Auto-zero tracking for one load cell, as weighing scales do it.
///
/// A handle's zero drifts as the clamp load on its cell relaxes in the printed
/// cartridge. While the handle reads near zero and holds still, the tracker
/// walks that handle's zero toward the reading at a capped rate; anything
/// bigger or moving freezes it. So a slow drift is followed, while a push,
/// even a light steady one, is not erased faster than `rate_n_per_s`. The total
/// correction since the last tare is capped, and the caller can show both the
/// correction and whether the tracker is active.
///
/// No ESP-IDF dependency: builds and tests on a host.
class ZeroTracker {
public:
  struct Config {
    float band_n{2.0f};        ///< track only while |reading| is below this
    float still_std_n{0.05f};  ///< ...and its std over the window is below this (a hand's
                               ///< tremor is well above it; an unloaded cell reads ~0.003 N)
    float window_s{2.0f};      ///< window for that mean and std
    float hold_s{5.0f};        ///< ...for at least this long
    float rate_n_per_s{0.005f}; ///< zero moves at most this fast (bench drift: ~0.0007 N/s)
    float max_n{10.0f};        ///< total correction since the last tare is capped here
    float sample_rate_hz{10.0f};
  };

  explicit ZeroTracker(const Config &config)
      : cfg_(config)
      , window_(std::max<size_t>(2, static_cast<size_t>(config.window_s * config.sample_rate_hz))) {}

  /// Feed one reading (newtons, tared, before this tracker's correction).
  /// Returns the corrected reading.
  float update(float raw_n) {
    const float dt = 1.0f / cfg_.sample_rate_hz;
    const float n = raw_n - offset_n_;
    window_[head_] = n;
    head_ = (head_ + 1) % window_.size();
    count_ = std::min(count_ + 1, window_.size());

    tracking_ = false;
    if (count_ == window_.size()) {
      float mean = 0, var = 0;
      for (float v : window_)
        mean += v;
      mean /= window_.size();
      for (float v : window_)
        var += (v - mean) * (v - mean);
      const float std = std::sqrt(var / (window_.size() - 1));
      const bool still = std::fabs(mean) < cfg_.band_n && std < cfg_.still_std_n;
      still_s_ = still ? still_s_ + dt : 0.0f;
      if (still_s_ >= cfg_.hold_s) {
        const float step = std::clamp(mean, -cfg_.rate_n_per_s * dt, cfg_.rate_n_per_s * dt);
        const float next = std::clamp(offset_n_ + step, -cfg_.max_n, cfg_.max_n);
        tracking_ = next != offset_n_;
        offset_n_ = next;
      }
    }
    return raw_n - offset_n_;
  }

  /// New thresholds and rates at run time (params). Keeps the correction and
  /// the window; window_s and sample_rate_hz are fixed at construction.
  void configure(const Config &config) {
    const float window_s = cfg_.window_s, rate_hz = cfg_.sample_rate_hz;
    cfg_ = config;
    cfg_.window_s = window_s;
    cfg_.sample_rate_hz = rate_hz;
    offset_n_ = std::clamp(offset_n_, -cfg_.max_n, cfg_.max_n);
  }

  /// Forget the correction (call after a tare).
  void reset() {
    offset_n_ = 0;
    still_s_ = 0;
    count_ = 0;
    head_ = 0;
    tracking_ = false;
  }

  float offset_n() const { return offset_n_; }       ///< correction applied, N
  bool tracking() const { return tracking_; }         ///< moved the zero on the last update
  bool at_limit() const { return std::fabs(offset_n_) >= cfg_.max_n; } ///< capped

protected:
  Config cfg_;
  std::vector<float> window_;
  size_t head_{0};
  size_t count_{0};
  float still_s_{0};
  float offset_n_{0};
  bool tracking_{false};
};
