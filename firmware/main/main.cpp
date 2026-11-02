// Push-assist handles: read one load cell per handle (two SparkFun HX711
// breakouts) and serve the forces over ethernet.
//
// EthLink carries the espp framed stream on tcp :5555 (UDP :5556 answers
// "PUSH?" discovery). On it:
//   module 3     espp::Telemetry: the six channels below, streamed once the
//                host sends SET_STREAM.
//   module 0x30  push_assist: TARE and GET_INFO (see PushAssistType).
// tools/eth_bridge.py serves web/dashboard.html and relays a WebSocket to the
// board's tcp :5555. With PA_CONSOLE_CSV the same rows also go to the UART0
// console on the USB-C, for `idf.py monitor` or a Web Serial plotter.
//
// Sign: push reads +. sum_N = left + right is the forward force; diff_N =
// left - right is + when the left handle pushes harder, i.e. a clockwise (right)
// turn seen from above, the same sense as rammp::XYTwist::twist.

#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <limits>
#include <span>
#include <string>
#include <thread>

#include <driver/temperature_sensor.h>
#include <esp_app_desc.h>

#include "coredump.hpp"
#include "ethernet.hpp"
#include "format.hpp"
#include "logger.hpp"
#include "stream_frame.hpp"
#include "task.hpp"
#include "telemetry.hpp"

#include "eth_link.hpp"
#include "load_cell.hpp"
#include "zero_tracker.hpp"

// A Kconfig bool set to n is left undefined in sdkconfig.h.
#ifdef CONFIG_PA_LEFT_INVERT
constexpr bool kLeftInvert = true;
#else
constexpr bool kLeftInvert = false;
#endif
#ifdef CONFIG_PA_RIGHT_INVERT
constexpr bool kRightInvert = true;
#else
constexpr bool kRightInvert = false;
#endif
#ifdef CONFIG_PA_ZERO_TRACKING
constexpr bool kZeroTracking = true;
#else
constexpr bool kZeroTracking = false;
#endif

using namespace std::chrono_literals;

namespace {

// HX711 at gain 128 with the bridge excited from its own AVDD (as on the
// SparkFun breakout): the full-scale input is +-0.5 * AVDD / 128 over +-2^23
// counts, so AVDD cancels and counts per V/V of bridge output = 128 * 2^24.
constexpr float kCountsPerVoltPerVolt = 128.0f * 16777216.0f;
constexpr float kGravity = 9.80665f;

float nominal_counts_per_newton() {
  const float rated_v_per_v = CONFIG_PA_CELL_RATED_UV_PER_V * 1e-6f;
  const float full_scale_n = CONFIG_PA_CELL_FULL_SCALE_KG * kGravity;
  return kCountsPerVoltPerVolt * rated_v_per_v / full_scale_n;
}

#if CONFIG_PA_HX711_80SPS
constexpr uint16_t kSamplesPerSecond = 80;
#else
constexpr uint16_t kSamplesPerSecond = 10;
#endif

constexpr float kNan = std::numeric_limits<float>::quiet_NaN();

// push_assist module: requests 0x0X, replies 0x8X (reply flag set).
constexpr uint8_t kPushAssistModule = 0x30;
enum class PushAssistType : uint8_t {
  Tare = 0x01,    ///< re-zero both cells (handles unloaded); answered with Tared
  GetInfo = 0x02, ///< answered with Info
  Tared = 0x81,   ///< [left_ok u8][right_ok u8]
  Info = 0x82,    ///< utf8 JSON: firmware, ip, scale, rate, pins, which cells answer
};

std::string ip_string(esp_ip4_addr_t ip) {
  return fmt::format("{}.{}.{}.{}", esp_ip4_addr1_16(&ip), esp_ip4_addr2_16(&ip),
                     esp_ip4_addr3_16(&ip), esp_ip4_addr4_16(&ip));
}

} // namespace

extern "C" void app_main(void) {
  espp::Logger logger({.tag = "push_assist", .level = espp::Logger::Verbosity::INFO});
  const std::string firmware = esp_app_get_description()->version;
  logger.info("Push-assist load cells, firmware {}", firmware);

  espp::CoreDump core_dump({.log_level = espp::Logger::Verbosity::INFO});
  const std::string crash_report = core_dump.format_report();
  if (!crash_report.empty())
    logger.error("Previous abnormal reset:\n{}", crash_report);

  // --- load cells --------------------------------------------------------------
  const float counts_per_newton = nominal_counts_per_newton();
  logger.info("Scale: {:.1f} counts/N ({} kg cell, {} uV/V, nominal)", counts_per_newton,
              CONFIG_PA_CELL_FULL_SCALE_KG, CONFIG_PA_CELL_RATED_UV_PER_V);

  LoadCell left({.name = "left",
                 .dout = static_cast<gpio_num_t>(CONFIG_PA_LEFT_DOUT_GPIO),
                 .sck = static_cast<gpio_num_t>(CONFIG_PA_LEFT_SCK_GPIO),
                 .counts_per_newton = counts_per_newton,
                 .invert = kLeftInvert,
                 .log_level = espp::Logger::Verbosity::INFO});
  LoadCell right({.name = "right",
                  .dout = static_cast<gpio_num_t>(CONFIG_PA_RIGHT_DOUT_GPIO),
                  .sck = static_cast<gpio_num_t>(CONFIG_PA_RIGHT_SCK_GPIO),
                  .counts_per_newton = counts_per_newton,
                  .invert = kRightInvert,
                  .log_level = espp::Logger::Verbosity::INFO});

  // GPIO 37 / 38 are UART0, the USB-C console (CH343P). An amp there takes the
  // pins from the console, and the CH343P's TXD drives GPIO 38 against the
  // HX711's DOUT while the USB-C is powered.
  for (int pin : {CONFIG_PA_LEFT_DOUT_GPIO, CONFIG_PA_LEFT_SCK_GPIO, CONFIG_PA_RIGHT_DOUT_GPIO,
                  CONFIG_PA_RIGHT_SCK_GPIO}) {
    if (pin == 37 || pin == 38) {
      logger.warn("An amp is on GPIO {} (UART0, the USB-C console): the console goes quiet "
                  "now, and that amp fights the CH343P while the USB-C is plugged in",
                  pin);
      break;
    }
  }

  // A cell that fails to come up is reported and streamed as NaN, so one amp
  // can be brought up on its own.
  logger.info("Taring: keep both handles unloaded");
  std::atomic<bool> left_ok{false};
  std::atomic<bool> right_ok{false};
  {
    std::error_code ec;
    left_ok = left.initialize(ec) && left.tare(CONFIG_PA_TARE_SAMPLES, ec);
    if (!left_ok)
      logger.error("Left HX711 not responding ({}): check DAT GPIO {}, CLK GPIO {}, 3V3, GND",
                   ec.message(), CONFIG_PA_LEFT_DOUT_GPIO, CONFIG_PA_LEFT_SCK_GPIO);
    ec.clear();
    right_ok = right.initialize(ec) && right.tare(CONFIG_PA_TARE_SAMPLES, ec);
    if (!right_ok)
      logger.error("Right HX711 not responding ({}): check DAT GPIO {}, CLK GPIO {}, 3V3, GND",
                   ec.message(), CONFIG_PA_RIGHT_DOUT_GPIO, CONFIG_PA_RIGHT_SCK_GPIO);
  }

  // --- ethernet ------------------------------------------------------------------
  // espp::Ethernet with the board's RMII pins and IP101GRI PHY, as the espp
  // esp32-p4-wifi6-poe-eth BSP sets them up. Not the BSP itself: its singleton
  // starts the internal I2C bus on GPIO 7 / 8 when it is constructed, and the
  // left amp may be wired there.
  espp::Ethernet::Config eth_config{};
  eth_config.interface = espp::Ethernet::RmiiConfig{
      .mdc_gpio = 31,
      .mdio_gpio = 52,
      .phy_addr = 1,
      .phy_reset_gpio = 51,
      .clock_ext_in = true, // the PHY makes the 50 MHz REF_CLK, the P4 takes it on GPIO 50
      .clock_gpio = 50,
      .data_pins = espp::Ethernet::RmiiConfig::DataPins{
          .tx_en = 49, .txd0 = 34, .txd1 = 35, .crs_dv = 28, .rxd0 = 29, .rxd1 = 30},
  };
#if CONFIG_PA_ETH_DHCP_SERVER
  // Bench, laptop straight into the board: the board serves 192.168.4.1/24 and
  // leases the laptop an address, so nothing else is needed on the link.
  eth_config.mode = espp::Ethernet::DhcpMode::SERVER;
  eth_config.on_client_assigned = [&](esp_ip4_addr_t ip, auto) {
    logger.info("Leased {} to a host", ip_string(ip));
  };
#else
  // On the chair the MIB is the DHCP server.
  eth_config.mode = espp::Ethernet::DhcpMode::CLIENT;
#endif
  eth_config.on_link_up = [&]() { logger.info("Ethernet link up"); };
  eth_config.on_link_down = [&]() { logger.warn("Ethernet link down"); };
  eth_config.on_got_ip = [&](esp_ip4_addr_t ip) { logger.info("Board at {}", ip_string(ip)); };
  eth_config.on_lost_ip = [&]() { logger.warn("Ethernet lost its IP"); };
  espp::Ethernet ethernet(eth_config);
  if (!ethernet.initialize())
    logger.error("Ethernet failed to start; forces go to the console only");

  auto info_json = [&]() {
    return fmt::format(
        R"({{"product":"push_assist","firmware":"{}","ip":"{}","left":{},"right":{},)"
        R"("counts_per_N":{:.2f},"full_scale_kg":{},"rated_uV_per_V":{},"sps":{},)"
        R"("pins":{{"left_dat":{},"left_clk":{},"right_dat":{},"right_clk":{}}},)"
        R"("invert":{{"left":{},"right":{}}},"zero_tracking":{}}})",
        firmware, ip_string(ethernet.ip()), left_ok.load(), right_ok.load(),
        counts_per_newton, CONFIG_PA_CELL_FULL_SCALE_KG, CONFIG_PA_CELL_RATED_UV_PER_V,
        kSamplesPerSecond, CONFIG_PA_LEFT_DOUT_GPIO, CONFIG_PA_LEFT_SCK_GPIO,
        CONFIG_PA_RIGHT_DOUT_GPIO, CONFIG_PA_RIGHT_SCK_GPIO, kLeftInvert, kRightInvert,
        kZeroTracking);
  };

  // --- zero tracking: follows the slow drift of each handle's zero ---------------
  const ZeroTracker::Config zt_config{.band_n = CONFIG_PA_ZT_BAND_MN / 1000.0f,
                                      .still_std_n = CONFIG_PA_ZT_STILL_STD_MN / 1000.0f,
                                      .rate_n_per_s = CONFIG_PA_ZT_RATE_UN_PER_S / 1e6f,
                                      .max_n = static_cast<float>(CONFIG_PA_ZT_MAX_N),
                                      .sample_rate_hz = kSamplesPerSecond};
  ZeroTracker left_zero(zt_config);
  ZeroTracker right_zero(zt_config);

  // The P4's on-die temperature sensor: board temperature, to line drift up
  // against warm-up. NaN if it does not start.
  temperature_sensor_handle_t tsens = nullptr;
  const temperature_sensor_config_t tsens_config = TEMPERATURE_SENSOR_CONFIG_DEFAULT(-10, 80);
  if (temperature_sensor_install(&tsens_config, &tsens) != ESP_OK ||
      temperature_sensor_enable(tsens) != ESP_OK) {
    logger.warn("Temperature sensor did not start");
    tsens = nullptr;
  }

  // --- telemetry: one float per channel, in this order --------------------------
  // *_zero_N is the tracker's correction (already taken out of *_N);
  // *_tracking is 1 while it is moving the zero, 2 when it is at its cap.
  espp::Telemetry telemetry({
      .channels = {"left_N", "right_N", "sum_N", "diff_N", "left_counts", "right_counts",
                   "left_zero_N", "right_zero_N", "left_tracking", "right_tracking",
                   "board_C"},
      // Stream only once a host connects and asks (SET_STREAM).
      .stream_on_start = false,
      .period_ms = static_cast<uint16_t>(1000 / kSamplesPerSecond), // informational
      .log_level = espp::Logger::Verbosity::WARN,
  });

  std::atomic<bool> tare_requested{false};
  EthLink link({.product = "Push Assist",
                .firmware = firmware,
                .info_json = info_json,
                .on_disconnect = [&]() { telemetry.set_streaming(false); }});
  telemetry.set_send([&](std::span<const uint8_t> f) { link.send(f); });
  link.worker().register_module(telemetry);

  auto reply = [&](PushAssistType type, std::span<const uint8_t> payload) {
    link.send(espp::stream_frame::build_frame(true, kPushAssistModule,
                                              static_cast<uint8_t>(type), payload));
  };
  link.worker().register_module(
      kPushAssistModule,
      [&](const espp::stream_frame::Frame &f) {
        if (f.is_reply())
          return;
        switch (static_cast<PushAssistType>(f.type)) {
        case PushAssistType::Tare:
          tare_requested = true; // the sample task tares and answers
          break;
        case PushAssistType::GetInfo: {
          const std::string json = info_json();
          reply(PushAssistType::Info,
                std::span(reinterpret_cast<const uint8_t *>(json.data()), json.size()));
          break;
        }
        default:
          break;
        }
      },
      {.name = "Push assist",
       .app = "dashboard.html",
       .description = "Tare and device info",
       .protocol = "rammp.push_assist",
       .protocol_version = 1});
  if (!link.start())
    logger.error("Ethernet service failed to start");

  // --- sample loop: runs at the HX711's conversion rate --------------------------
  // Both HX711s free-run at the same rate, so reading one then the other picks
  // up conversions at most one period apart.
#if CONFIG_PA_CONSOLE_CSV
  const auto t0 = std::chrono::steady_clock::now();
  size_t row = 0;
#endif
  auto sample_fn = [&](std::mutex &, std::condition_variable &) {
    std::error_code ec;
    if (tare_requested.exchange(false)) {
      logger.info("Tare requested over ethernet");
      if (left_ok)
        left_ok = left.tare(CONFIG_PA_TARE_SAMPLES, ec);
      ec.clear();
      if (right_ok)
        right_ok = right.tare(CONFIG_PA_TARE_SAMPLES, ec);
      ec.clear();
      left_zero.reset();
      right_zero.reset();
      const std::array<uint8_t, 2> done = {left_ok.load(), right_ok.load()};
      reply(PushAssistType::Tared, done);
    }
    const bool have_left = left_ok && left.update(ec);
    ec.clear();
    const bool have_right = right_ok && right.update(ec);
    if (!have_left && !have_right) {
      std::this_thread::sleep_for(500ms); // nothing wired: don't spin
      return false;
    }
    auto track = [](ZeroTracker &z, bool have, float n) {
      return !have ? kNan : kZeroTracking ? z.update(n) : n;
    };
    auto state = [](const ZeroTracker &z, bool have) {
      return !have ? kNan : z.at_limit() ? 2.0f : z.tracking() ? 1.0f : 0.0f;
    };
    const float l = track(left_zero, have_left, have_left ? left.newtons() : 0);
    const float r = track(right_zero, have_right, have_right ? right.newtons() : 0);
    float board_c = kNan;
    if (tsens)
      temperature_sensor_get_celsius(tsens, &board_c);
    const std::array<float, 11> values = {
        l,
        r,
        l + r,
        l - r,
        have_left ? static_cast<float>(left.counts()) : kNan,
        have_right ? static_cast<float>(right.counts()) : kNan,
        have_left ? left_zero.offset_n() : kNan,
        have_right ? right_zero.offset_n() : kNan,
        state(left_zero, have_left),
        state(right_zero, have_right),
        board_c,
    };
    telemetry.emit(values); // no-op until a host turns streaming on
#if CONFIG_PA_CONSOLE_CSV
    if (row++ % 100 == 0)
      fmt::print("time_s,left_N,right_N,sum_N,diff_N,left_counts,right_counts,left_zero_N,"
                 "right_zero_N,left_tracking,right_tracking,board_C\n");
    const float t = std::chrono::duration<float>(std::chrono::steady_clock::now() - t0).count();
    fmt::print("{:.3f},{:.3f},{:.3f},{:.3f},{:.3f},{:.0f},{:.0f},{:.3f},{:.3f},{:.0f},{:.0f},{:.1f}\n",
               t, values[0], values[1], values[2], values[3], values[4], values[5], values[6],
               values[7], values[8], values[9], values[10]);
#endif
    return false; // keep running
  };
  auto sample_task = espp::Task::make_unique(
      {.callback = sample_fn, .task_config = {.name = "load_cells", .stack_size_bytes = 6144}});
  sample_task->start();

  logger.info("Running. On a laptop on the same network: python3 tools/eth_bridge.py, then "
              "open http://localhost:8765/");

  while (true) {
    std::this_thread::sleep_for(1s);
  }
}
