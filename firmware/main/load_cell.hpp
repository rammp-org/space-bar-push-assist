#pragma once

#include <chrono>
#include <cstdint>
#include <string_view>
#include <system_error>

#include <driver/gpio.h>
#include <hx711.h>

#include "base_component.hpp"

/// One load cell on a SparkFun HX711 breakout (channel A, gain 128).
///
/// A thin espp-style wrapper over the esp-idf-lib HX711 driver, which does the
/// bit-banged read (24 clocks plus the gain pulse, inside a critical section so
/// PD_SCK never stays high long enough to power the chip down). This class adds
/// the tare, the sign (push reads +) and the scale to newtons.
///
/// update() blocks until the HX711 has a new conversion (10 or 80 samples/s, set
/// by its RATE pin), so a loop calling it runs at the converter's rate.
class LoadCell : public espp::BaseComponent {
public:
  struct Config {
    std::string_view name;   ///< Log tag, e.g. "left".
    gpio_num_t dout;         ///< HX711 DAT (DOUT).
    gpio_num_t sck;          ///< HX711 CLK (PD_SCK).
    float counts_per_newton; ///< Tared counts per newton (> 0).
    bool invert{false};      ///< Flip the sign so that push reads +.
    std::chrono::milliseconds timeout{std::chrono::milliseconds(250)}; ///< Wait for a conversion.
    espp::Logger::Verbosity log_level{espp::Logger::Verbosity::WARN};
  };

  explicit LoadCell(const Config &config)
      : BaseComponent(config.name, config.log_level)
      , dev_{.dout = config.dout, .pd_sck = config.sck, .gain = HX711_GAIN_A_128}
      , counts_per_newton_(config.counts_per_newton)
      , sign_(config.invert ? -1 : 1)
      , timeout_(config.timeout) {}

  /// Configure the pins, power the HX711 up and set gain 128. Fails if the
  /// HX711 does not report a conversion within the timeout (not wired, or no
  /// power).
  bool initialize(std::error_code &ec) {
    // hx711_init() powers the chip up and waits 200 ms for a conversion to set
    // the gain, but the HX711 needs about 400 ms to settle after power-up at
    // 10 samples/s. On that timeout, wait the full settling time and set the
    // gain again.
    esp_err_t err = hx711_init(&dev_);
    if (err == ESP_ERR_TIMEOUT && hx711_wait(&dev_, kPowerUpMs) == ESP_OK)
      err = hx711_set_gain(&dev_, dev_.gain);
    if (err != ESP_OK)
      logger_.error("no conversion after {} ms: DOUT (GPIO {}) reads {}", kPowerUpMs,
                    static_cast<int>(dev_.dout), gpio_get_level(dev_.dout));
    if (!check(err, "init", ec))
      return false;
    logger_.info("HX711 on DOUT {} / SCK {} ready", static_cast<int>(dev_.dout),
                 static_cast<int>(dev_.pd_sck));
    return true;
  }

  /// Average `samples` readings and use them as zero. The cell must be unloaded.
  bool tare(size_t samples, std::error_code &ec) {
    int64_t sum = 0;
    for (size_t i = 0; i < samples; i++) {
      if (!update(ec))
        return false;
      sum += raw_;
    }
    offset_ = static_cast<int32_t>(sum / static_cast<int64_t>(samples));
    logger_.info("tare offset {} counts ({} readings)", offset_, samples);
    return true;
  }

  /// Wait for the next conversion and read it.
  bool update(std::error_code &ec) {
    if (!check(hx711_wait(&dev_, timeout_.count()), "wait", ec))
      return false;
    int32_t value = 0;
    if (!check(hx711_read_data(&dev_, &value), "read", ec))
      return false;
    raw_ = value;
    return true;
  }

  /// Last reading as the HX711 gave it (signed 24-bit).
  int32_t raw() const { return raw_; }

  /// Last reading less the tare, push +.
  int32_t counts() const { return sign_ * (raw_ - offset_); }

  /// Last reading in newtons, push +.
  float newtons() const { return static_cast<float>(counts()) / counts_per_newton_; }

protected:
  static constexpr size_t kPowerUpMs = 1000; ///< > 400 ms settling at 10 samples/s

  bool check(esp_err_t err, std::string_view what, std::error_code &ec) {
    if (err == ESP_OK)
      return true;
    ec = std::make_error_code(err == ESP_ERR_TIMEOUT ? std::errc::timed_out : std::errc::io_error);
    logger_.error_rate_limited("{} failed: {}", what, esp_err_to_name(err));
    return false;
  }

  hx711_t dev_;
  float counts_per_newton_;
  int sign_;
  std::chrono::milliseconds timeout_;
  int32_t raw_{0};
  int32_t offset_{0};
};
