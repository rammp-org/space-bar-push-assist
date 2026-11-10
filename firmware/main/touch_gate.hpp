#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <deque>
#include <limits>
#include <numeric>

/// A handle's touch switch and touch tare (bench log 2026-11-10,
/// firmware/logs/touch_handle_20261110_0047.csv).
///
/// Touch: the pad's reading rises 11-12 % above its idle baseline under a hand
/// (idle noise about 0.02 %), and it rises 0.3-0.8 s before the push does.
/// The baseline is this class's own: it follows the reading while the pad is
/// idle and holds while it is touched (the P4's hardware benchmark froze when a
/// probe was attached and never let go). On above on_pct, off below off_pct.
///
/// Tare: on each touch the force zero becomes the mean force over the window
/// that ends gap before the touch, so whatever the handle read hands-off (the
/// 6-10 N it kept after a push on the bench) is taken out. Switch: untouched,
/// the handle reads 0.
///
/// No ESP-IDF dependency: builds and replays logs on a host.
class TouchGate {
public:
  struct Config {
    float on_pct{8.0f};         ///< touched above this, % of the baseline
    float off_pct{4.0f};        ///< released below this
    float baseline_tau_s{10.0f}; ///< idle baseline follows with this time constant
    float tare_window_s{1.0f};  ///< force averaged over this long ...
    float tare_gap_s{0.2f};     ///< ... ending this long before the touch
    float stuck_s{30.0f};        ///< touched this long with the force still: re-take the baseline
    float sample_rate_hz{10.0f};
    bool gate{true};            ///< false: pass the force through (touch still reported)
  };

  TouchGate() { configure(Config{}); }
  explicit TouchGate(const Config &config) { configure(config); }

  void configure(const Config &c) {
    cfg_ = c;
    window_ = std::max<size_t>(1, static_cast<size_t>(std::lround(c.tare_window_s * c.sample_rate_hz)));
    gap_ = static_cast<size_t>(std::lround(c.tare_gap_s * c.sample_rate_hz));
    alpha_ = std::min(1.0f, 1.0f / (c.baseline_tau_s * c.sample_rate_hz));
    stuck_n_ = static_cast<size_t>(std::lround(c.stuck_s * c.sample_rate_hz));
    while (history_.size() > window_ + gap_)
      history_.pop_front();
  }

  /// One sample: the pad's raw reading (NaN if no pad) and the handle force
  /// in N (NaN if no amp). Returns the force to send.
  float update(float raw, float force) {
    if (!std::isfinite(raw)) { // no pad: the old behaviour
      touched_ = false;
      pct_ = kNan;
      return force;
    }
    if (!has_base_ || rebase_) {
      base_ = raw;
      has_base_ = true;
      rebase_ = false;
      touched_ = false;
    }
    pct_ = base_ > 0 ? 100.0f * (raw - base_) / base_ : 0.0f;
    if (!touched_ && pct_ > cfg_.on_pct) {
      touched_ = true;
      tare_ = pre_touch_mean();
    } else if (touched_ && pct_ < cfg_.off_pct) {
      touched_ = false;
    }
    // The baseline follows only a pad that is clearly idle: a light grip that
    // stays under on_pct would otherwise be soaked into it, and the reading
    // would drop below 0 on release.
    if (!touched_ && pct_ < cfg_.off_pct)
      base_ += (raw - base_) * alpha_;
    // A reading that jumped and stayed (a probe plugged in, a wire moved) with
    // no force behind it is not a hand: after stuck_s, it becomes the baseline.
    still_ = touched_ && std::isfinite(force) && std::fabs(force - tare_) < kStillN ? still_ + 1 : 0;
    if (still_ > stuck_n_) {
      base_ = raw;
      touched_ = false;
      still_ = 0;
    }
    if (std::isfinite(force)) {
      history_.push_back(force);
      if (history_.size() > window_ + gap_)
        history_.pop_front();
    }
    if (!cfg_.gate)
      return force;
    return touched_ ? force - tare_ : (std::isfinite(force) ? 0.0f : force);
  }

  /// Take the next reading as the idle baseline (hands off: tare time).
  void rebaseline() { rebase_ = true; }

  bool touched() const { return touched_; }
  float percent() const { return pct_; }   ///< reading above the baseline, %
  float baseline() const { return base_; }
  float tare() const { return tare_; }      ///< force zero of the current (or last) touch, N

protected:
  static constexpr float kNan = std::numeric_limits<float>::quiet_NaN();
  static constexpr float kStillN = 2.0f; // "no force behind it", N

  // Mean of the oldest `window_` samples, i.e. the window that ends `gap_`
  // samples before now. Fewer samples at start-up: whatever there is.
  float pre_touch_mean() const {
    if (history_.empty())
      return 0.0f;
    const size_t n = history_.size() > gap_ ? history_.size() - gap_ : history_.size();
    const size_t k = std::min(n, window_);
    return std::accumulate(history_.begin() + (n - k), history_.begin() + n, 0.0f) /
           static_cast<float>(k);
  }

  Config cfg_;
  size_t window_{10}, gap_{2}, stuck_n_{300}, still_{0};
  float alpha_{0.01f};
  std::deque<float> history_;
  float base_{0}, pct_{kNan}, tare_{0};
  bool has_base_{false}, rebase_{false}, touched_{false};
};
