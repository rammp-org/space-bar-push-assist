#pragma once

#include <array>
#include <cstdint>
#include <limits>
#include <system_error>

#include <driver/touch_sens.h>

#include "base_component.hpp"

/// The ESP32-P4's capacitive touch sensor (touch v3) reading up to two pads,
/// one per handle.
///
/// A thin wrapper over ESP-IDF's esp_driver_touch_sens, set up the way its
/// touch_sens_basic example does it: one sample configuration, the default
/// filters, continuous scanning. It only reports each pad's smoothed reading;
/// what counts as a touch is TouchGate's call (touch_gate.hpp), because the
/// hardware's own benchmark and active flag froze when a probe was attached.
///
/// On the P4 the pads are GPIO 2 to 15, touch channel = GPIO - 1. The driver
/// has one controller, so both pads live in one object.
class TouchPads : public espp::BaseComponent {
public:
  static constexpr size_t kMaxPads = 2;

  explicit TouchPads(espp::Logger::Verbosity log_level = espp::Logger::Verbosity::WARN)
      : BaseComponent("touch", log_level) {}

  ~TouchPads() {
    if (!sens_)
      return;
    touch_sensor_stop_continuous_scanning(sens_);
    touch_sensor_disable(sens_);
    for (auto chan : chan_)
      if (chan)
        touch_sensor_del_channel(chan);
    touch_sensor_del_controller(sens_);
  }

  /// Start scanning the given pads; a GPIO of 0 is no pad. Returns which pads
  /// came up (a bad GPIO leaves the others running).
  std::array<bool, kMaxPads> start(std::array<int, kMaxPads> gpios, std::error_code &ec) {
    std::array<bool, kMaxPads> ok{};
    touch_sensor_sample_config_t sample[TOUCH_SAMPLE_CFG_NUM] = {
        TOUCH_SENSOR_V3_DEFAULT_SAMPLE_CONFIG2(3, 29, 8, 3)};
    touch_sensor_config_t sens_cfg = TOUCH_SENSOR_DEFAULT_BASIC_CONFIG(1, sample);
    touch_sensor_filter_config_t filter_cfg = TOUCH_SENSOR_DEFAULT_FILTER_CONFIG();
    if (!check(touch_sensor_new_controller(&sens_cfg, &sens_), "new controller", ec))
      return ok;
    for (size_t i = 0; i < kMaxPads; i++) {
      const int gpio = gpios[i];
      if (gpio == 0)
        continue;
      if (gpio < 2 || gpio > 15) {
        logger_.error("GPIO {} has no touch channel on the P4 (pads are GPIO 2 to 15)", gpio);
        continue;
      }
      touch_channel_config_t chan_cfg = {.active_thresh = {1000}}; // unused: TouchGate decides
      std::error_code chan_ec;
      ok[i] = check(touch_sensor_new_channel(sens_, gpio - 1, &chan_cfg, &chan_[i]),
                    "new channel", chan_ec);
      if (ok[i])
        logger_.info("Touch pad {} on GPIO {} (channel {})", i, gpio, gpio - 1);
    }
    if (!check(touch_sensor_config_filter(sens_, &filter_cfg), "filter", ec) ||
        !check(touch_sensor_enable(sens_), "enable", ec))
      return {};
    // A few one-shot scans so the first readings are real (the IDF example's
    // initial scanning), then continuous scanning.
    for (int k = 0; k < 3; k++)
      if (!check(touch_sensor_trigger_oneshot_scanning(sens_, 2000), "initial scan", ec))
        return {};
    if (!check(touch_sensor_start_continuous_scanning(sens_), "start", ec))
      return {};
    return ok;
  }

  /// A pad's smoothed reading in raw counts (it rises with touch on v3), or
  /// NaN if that pad is not running.
  float read(size_t i) const {
    uint32_t data[TOUCH_SAMPLE_CFG_NUM] = {};
    if (i >= kMaxPads || !chan_[i] ||
        touch_channel_read_data(chan_[i], TOUCH_CHAN_DATA_TYPE_SMOOTH, data) != ESP_OK)
      return std::numeric_limits<float>::quiet_NaN();
    return static_cast<float>(data[0]);
  }

protected:
  bool check(esp_err_t err, const char *what, std::error_code &ec) {
    if (err == ESP_OK)
      return true;
    logger_.error("Touch {} failed: {}", what, esp_err_to_name(err));
    ec = std::make_error_code(std::errc::io_error);
    return false;
  }

  touch_sensor_handle_t sens_{nullptr};
  std::array<touch_channel_handle_t, kMaxPads> chan_{};
};
