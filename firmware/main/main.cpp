// Push-assist handles: read one load cell per handle (two SparkFun HX711
// breakouts), publish the forces to the MIB over RTPS, and serve data, params
// and OTA over ethernet. The interface is written down in firmware/INTERFACE.md.
//
// RTPS: rammp::HandleForce on rammp/push_assist/handle_force (rammp-rtps),
// one sample per conversion. The MIB turns it into drive commands
// (docs/MIB-INPUT-DEVICES.md).
//
// EthLink carries the espp framed stream on tcp :5555 (UDP :5556 answers
// "PUSH?" discovery). On it:
//   module 0     espp::OtaService: firmware update, with a rollback gate.
//   module 3     espp::Telemetry: the channels below, streamed once the host
//                sends SET_STREAM.
//   module 0x30  push_assist: TARE, GET_INFO and the self-describing params
//                (see PushAssistType).
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
#include <cstring>
#include <limits>
#include <memory>
#include <mutex>
#include <span>
#include <string>
#include <thread>

#include <driver/temperature_sensor.h>
#include <driver/uart.h>
#include <driver/uart_vfs.h>
#include <esp_app_desc.h>
#include <nvs.h>
#include <nvs_flash.h>

#include "coredump.hpp"
#include "ethernet.hpp"
#include "format.hpp"
#include "logger.hpp"
#include "ota.hpp"
#include "ota_service.hpp"
#include "rtps_participant.hpp"
#include "rtps_pubsub.hpp"
#include "stream_frame.hpp"
#include "task.hpp"
#include "telemetry.hpp"

#include "messages/push_assist_message.hpp"

#include "eth_link.hpp"
#include "load_cell.hpp"
#include "params.hpp"
#include "touch_gate.hpp"
#include "touch_probe.hpp"
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

float counts_per_newton(float full_scale_kg, float rated_uv_per_v) {
  return kCountsPerVoltPerVolt * rated_uv_per_v * 1e-6f / (full_scale_kg * kGravity);
}

#if CONFIG_PA_HX711_80SPS
constexpr uint16_t kSamplesPerSecond = 80;
#else
constexpr uint16_t kSamplesPerSecond = 10;
#endif

constexpr float kNan = std::numeric_limits<float>::quiet_NaN();

// A new image confirms itself once it holds a lease and has served the stream
// this long (PACE RACER's rollback gate); until then a reset rolls it back.
constexpr auto kSelfVerifyAfter = 20s;

// push_assist module: requests 0x0X, replies 0x8X (reply flag set).
constexpr uint8_t kPushAssistModule = 0x30;
enum class PushAssistType : uint8_t {
  Tare = 0x01,          ///< re-zero both cells (handles unloaded); answered with Tared
  GetInfo = 0x02,       ///< answered with Info
  GetParams = 0x03,     ///< answered with Params
  SetParam = 0x04,      ///< [key_len u8][key][value f32]; answered with Param
  SaveParams = 0x05,    ///< commit to NVS; answered with Saved
  DefaultParams = 0x06, ///< Kconfig defaults in RAM; answered with Defaults
  Tared = 0x81,         ///< [left_ok u8][right_ok u8]
  Info = 0x82,          ///< utf8 JSON: image, ip, scale, rate, pins, which cells answer
  Params = 0x83,        ///< utf8 JSON {"params":[...]}
  Param = 0x84,         ///< utf8 JSON: the one param after apply (clamped)
  Saved = 0x85,         ///< [ok u8]
  Defaults = 0x86,      ///< utf8 JSON {"params":[...]}
  Error = 0x8F,         ///< [request type u8][utf8 message]
};

std::string ip_string(esp_ip4_addr_t ip) {
  return fmt::format("{}.{}.{}.{}", esp_ip4_addr1_16(&ip), esp_ip4_addr2_16(&ip),
                     esp_ip4_addr3_16(&ip), esp_ip4_addr4_16(&ip));
}

std::span<const uint8_t> bytes(std::string_view s) {
  return {reinterpret_cast<const uint8_t *>(s.data()), s.size()};
}

// The runtime params; their defaults are the Kconfig values. Pins and the RATE
// flag stay compile-time (GET_INFO reports them).
std::vector<ParamTable::Def> param_defs() {
  using T = ParamTable::Type;
  return {
      {"invert_left", "Invert left cell", "", "Cells", T::Bool, kLeftInvert, 0, 1, 1},
      {"invert_right", "Invert right cell", "", "Cells", T::Bool, kRightInvert, 0, 1, 1},
      {"full_scale_kg", "Cell full scale", "kg", "Cells", T::Float,
       static_cast<float>(CONFIG_PA_CELL_FULL_SCALE_KG), 1, 500, 1},
      {"rated_uv_per_v", "Cell rated output", "uV/V", "Cells", T::Float,
       static_cast<float>(CONFIG_PA_CELL_RATED_UV_PER_V), 100, 5000, 1},
      {"tare_samples", "Tare readings", "readings", "Cells", T::Float,
       static_cast<float>(CONFIG_PA_TARE_SAMPLES), 1, 255, 1},
      {"zero_tracking", "Zero tracking", "", "Zero tracking", T::Bool, kZeroTracking, 0, 1, 1},
#ifdef CONFIG_PA_ZERO_TRACKING
      {"zt_band_n", "Zero-track band", "N", "Zero tracking", T::Float,
       CONFIG_PA_ZT_BAND_MN / 1000.0f, 0, 20, 0.1f},
      {"zt_still_std_n", "Still below (2 s std)", "N", "Zero tracking", T::Float,
       CONFIG_PA_ZT_STILL_STD_MN / 1000.0f, 0, 1, 0.005f},
      {"zt_rate_n_per_s", "Max zero rate", "N/s", "Zero tracking", T::Float,
       CONFIG_PA_ZT_RATE_UN_PER_S / 1e6f, 0, 0.1f, 0.0005f},
      {"zt_max_n", "Max correction since tare", "N", "Zero tracking", T::Float,
       static_cast<float>(CONFIG_PA_ZT_MAX_N), 0, 100, 1},
#else
      {"zt_band_n", "Zero-track band", "N", "Zero tracking", T::Float, 2.0f, 0, 20, 0.1f},
      {"zt_still_std_n", "Still below (2 s std)", "N", "Zero tracking", T::Float, 0.05f, 0, 1,
       0.005f},
      {"zt_rate_n_per_s", "Max zero rate", "N/s", "Zero tracking", T::Float, 0.005f, 0, 0.1f,
       0.0005f},
      {"zt_max_n", "Max correction since tare", "N", "Zero tracking", T::Float, 10, 0, 100, 1},
#endif
      {"touch_gate", "Touch switch and tare", "", "Touch", T::Bool, 1, 0, 1, 1},
      // Per handle: the pads differ with how the wire sits in the grip (bench
      // 2026-11-10: left grips 10-13 % above idle, right 3.5-8 %).
      {"touch_l_on_pct", "Left touched above", "%", "Touch", T::Float, 8.0f, 0.5f, 50, 0.1f},
      {"touch_l_off_pct", "Left released below", "%", "Touch", T::Float, 4.0f, 0.2f, 50, 0.1f},
      {"touch_r_on_pct", "Right touched above", "%", "Touch", T::Float, 3.0f, 0.5f, 50, 0.1f},
      {"touch_r_off_pct", "Right released below", "%", "Touch", T::Float, 1.5f, 0.2f, 50, 0.1f},
  };
}

// Params in NVS: one u32 (the float's bits) per key, namespace "push_assist".
constexpr const char *kNvsNamespace = "push_assist";

void load_params(ParamTable &params, espp::Logger &logger) {
  nvs_handle_t h;
  if (nvs_open(kNvsNamespace, NVS_READONLY, &h) != ESP_OK)
    return; // nothing saved yet
  int loaded = 0;
  for (const auto &d : params.defs()) {
    uint32_t bits;
    if (nvs_get_u32(h, d.key.c_str(), &bits) == ESP_OK) {
      float v;
      std::memcpy(&v, &bits, sizeof v);
      params.set(d.key, v);
      loaded++;
    }
  }
  nvs_close(h);
  logger.info("Loaded {} saved params from NVS", loaded);
}

bool save_params(const ParamTable &params, espp::Logger &logger) {
  nvs_handle_t h;
  esp_err_t err = nvs_open(kNvsNamespace, NVS_READWRITE, &h);
  for (const auto &d : params.defs()) {
    if (err != ESP_OK)
      break;
    const float v = params.get(d.key);
    uint32_t bits;
    std::memcpy(&bits, &v, sizeof bits);
    err = nvs_set_u32(h, d.key.c_str(), bits);
  }
  if (err == ESP_OK)
    err = nvs_commit(h);
  nvs_close(h);
  if (err != ESP_OK)
    logger.error("Saving params failed: {}", esp_err_to_name(err));
  return err == ESP_OK;
}

} // namespace

extern "C" void app_main(void) {
  espp::Logger logger({.tag = "push_assist", .level = espp::Logger::Verbosity::INFO});
  const esp_app_desc_t *app = esp_app_get_description();
  const std::string firmware = app->version;
  logger.info("Push-assist load cells, {} {} (built {} {})", app->project_name, firmware,
              app->date, app->time);

  espp::CoreDump core_dump({.log_level = espp::Logger::Verbosity::INFO});
  const std::string crash_report = core_dump.format_report();
  if (!crash_report.empty())
    logger.error("Previous abnormal reset:\n{}", crash_report);

  espp::Ota ota({.reject_same_version = false, .log_level = espp::Logger::Verbosity::INFO});
  const bool booted_pending = ota.is_pending_verify();
  if (booted_pending)
    logger.warn("New image, PENDING VERIFY: it confirms itself after a lease and {} s of "
                "service, or a host sends MARK_VALID; a reset before that rolls it back",
                std::chrono::duration_cast<std::chrono::seconds>(kSelfVerifyAfter).count());

  // --- params: Kconfig defaults, then whatever was saved -----------------------
  esp_err_t nvs_err = nvs_flash_init();
  if (nvs_err == ESP_ERR_NVS_NO_FREE_PAGES || nvs_err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    nvs_flash_erase();
    nvs_err = nvs_flash_init();
  }
  if (nvs_err != ESP_OK)
    logger.error("NVS failed to start ({}): params will not persist", esp_err_to_name(nvs_err));
  ParamTable params(param_defs());
  load_params(params, logger);

  auto scale = [&]() {
    return counts_per_newton(params.get("full_scale_kg"), params.get("rated_uv_per_v"));
  };
  logger.info("Scale: {:.1f} counts/N ({} kg cell, {} uV/V, nominal)", scale(),
              params.get("full_scale_kg"), params.get("rated_uv_per_v"));

  // --- load cells --------------------------------------------------------------
  LoadCell left({.name = "left",
                 .dout = static_cast<gpio_num_t>(CONFIG_PA_LEFT_DOUT_GPIO),
                 .sck = static_cast<gpio_num_t>(CONFIG_PA_LEFT_SCK_GPIO),
                 .counts_per_newton = scale(),
                 .invert = params.get_bool("invert_left"),
                 .log_level = espp::Logger::Verbosity::INFO});
  LoadCell right({.name = "right",
                  .dout = static_cast<gpio_num_t>(CONFIG_PA_RIGHT_DOUT_GPIO),
                  .sck = static_cast<gpio_num_t>(CONFIG_PA_RIGHT_SCK_GPIO),
                  .counts_per_newton = scale(),
                  .invert = params.get_bool("invert_right"),
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
    const size_t tare_n = static_cast<size_t>(params.get("tare_samples"));
    std::error_code ec;
    left_ok = left.initialize(ec) && left.tare(tare_n, ec);
    if (!left_ok)
      logger.error("Left HX711 not responding ({}): check DAT GPIO {}, CLK GPIO {}, 3V3, GND",
                   ec.message(), CONFIG_PA_LEFT_DOUT_GPIO, CONFIG_PA_LEFT_SCK_GPIO);
    ec.clear();
    right_ok = right.initialize(ec) && right.tare(tare_n, ec);
    if (!right_ok)
      logger.error("Right HX711 not responding ({}): check DAT GPIO {}, CLK GPIO {}, 3V3, GND",
                   ec.message(), CONFIG_PA_RIGHT_DOUT_GPIO, CONFIG_PA_RIGHT_SCK_GPIO);
  }

  // --- touch pads: each handle's switch and tare (touch_gate.hpp) ----------------
  // With a pad, a handle reads 0 N untouched, and on each touch its zero becomes
  // the force it read just before. Without one it reads as before.
  TouchPads pads(espp::Logger::Verbosity::INFO);
  std::array<bool, 2> pad_ok{};
  {
    std::error_code ec;
    pad_ok = pads.start({CONFIG_PA_TOUCH_LEFT_GPIO, CONFIG_PA_TOUCH_RIGHT_GPIO}, ec);
    for (int i = 0; i < 2; i++)
      if ((i ? CONFIG_PA_TOUCH_RIGHT_GPIO : CONFIG_PA_TOUCH_LEFT_GPIO) != 0 && !pad_ok[i])
        logger.error("{} touch pad did not start: that handle reads without the touch switch",
                     i ? "Right" : "Left");
  }
  const bool touch_ok = pad_ok[0] || pad_ok[1];
  auto gate_config = [&](bool right_side) {
    return TouchGate::Config{.on_pct = params.get(right_side ? "touch_r_on_pct" : "touch_l_on_pct"),
                             .off_pct = params.get(right_side ? "touch_r_off_pct" : "touch_l_off_pct"),
                             .sample_rate_hz = kSamplesPerSecond,
                             .gate = params.get_bool("touch_gate")};
  };
  TouchGate left_gate(gate_config(false));
  TouchGate right_gate(gate_config(true));

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
        R"({{"product":"push_assist","project":"{}","firmware":"{}","built":"{} {}",)"
        R"("partition":"{}","pending_verify":{},"ip":"{}","left":{},"right":{},)"
        R"("counts_per_N":{:.2f},"full_scale_kg":{},"rated_uV_per_V":{},"sps":{},)"
        R"("pins":{{"left_dat":{},"left_clk":{},"right_dat":{},"right_clk":{}}},)"
        R"("invert":{{"left":{},"right":{}}},"zero_tracking":{},)"
        R"("touch":{{"left_gpio":{},"right_gpio":{},"left":{},"right":{},"gate":{}}}}})",
        app->project_name, firmware, app->date, app->time, ota.running_partition_label(),
        ota.is_pending_verify(), ip_string(ethernet.ip()), left_ok.load(), right_ok.load(),
        scale(), params.get("full_scale_kg"), params.get("rated_uv_per_v"), kSamplesPerSecond,
        CONFIG_PA_LEFT_DOUT_GPIO, CONFIG_PA_LEFT_SCK_GPIO, CONFIG_PA_RIGHT_DOUT_GPIO,
        CONFIG_PA_RIGHT_SCK_GPIO, params.get_bool("invert_left"),
        params.get_bool("invert_right"), params.get_bool("zero_tracking"),
        CONFIG_PA_TOUCH_LEFT_GPIO, CONFIG_PA_TOUCH_RIGHT_GPIO, pad_ok[0], pad_ok[1],
        params.get_bool("touch_gate"));
  };

  // --- zero tracking: follows the slow drift of each handle's zero ---------------
  auto zt_config = [&]() {
    return ZeroTracker::Config{.band_n = params.get("zt_band_n"),
                               .still_std_n = params.get("zt_still_std_n"),
                               .rate_n_per_s = params.get("zt_rate_n_per_s"),
                               .max_n = params.get("zt_max_n"),
                               .sample_rate_hz = kSamplesPerSecond};
  };
  ZeroTracker left_zero(zt_config());
  ZeroTracker right_zero(zt_config());

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
  // left_N / right_N are what the MIB gets: with a touch pad, tared on each
  // touch and 0 untouched. *_ungated_N is the force before that, *_touch_pct the
  // pad above its idle baseline, *_touched 0/1, *_tare_N the zero of the
  // current (or last) touch, *_touch_raw the pad's reading in counts. NaN with
  // no pad.
  espp::Telemetry telemetry({
      .channels = {"left_N", "right_N", "sum_N", "diff_N", "left_counts", "right_counts",
                   "left_zero_N", "right_zero_N", "left_tracking", "right_tracking",
                   "board_C", "left_ungated_N", "right_ungated_N", "left_touch_pct",
                   "right_touch_pct", "left_touched", "right_touched", "left_tare_N",
                   "right_tare_N", "left_touch_raw", "right_touch_raw"},
      // Stream only once a host connects and asks (SET_STREAM).
      .stream_on_start = false,
      .period_ms = static_cast<uint16_t>(1000 / kSamplesPerSecond), // informational
      .log_level = espp::Logger::Verbosity::WARN,
  });

  // --- the service stream: OTA, telemetry, push_assist ---------------------------
  std::unique_ptr<espp::OtaService> ota_service;
  EthLink link({.product = "Push Assist",
                .firmware = firmware,
                .info_json = info_json,
                .on_disconnect = [&]() { telemetry.set_streaming(false); },
                .on_overflow = [&]() {
                  if (ota_service)
                    ota_service->on_rx_overflow();
                }});
  ota_service = std::make_unique<espp::OtaService>(
      ota, espp::OtaService::Config{.send = [&](std::span<const uint8_t> f) { link.send(f); },
                                    .log_level = espp::Logger::Verbosity::INFO});
  link.worker().register_module(*ota_service);
  telemetry.set_send([&](std::span<const uint8_t> f) { link.send(f); });
  link.worker().register_module(telemetry);

  std::atomic<bool> tare_requested{false};
  std::atomic<bool> console_tare{false}; // answer the tare on the console too
  auto reply = [&](PushAssistType type, std::span<const uint8_t> payload) {
    link.send(espp::stream_frame::build_frame(true, kPushAssistModule,
                                              static_cast<uint8_t>(type), payload));
  };
  auto reply_error = [&](uint8_t request, std::string_view message) {
    std::vector<uint8_t> p{request};
    p.insert(p.end(), message.begin(), message.end());
    reply(PushAssistType::Error, p);
  };
  // Shared by the ethernet module and the USB-C console commands.
  auto set_param = [&](const std::string &key, float value, std::string &out) {
    const auto i = params.set(key, value);
    if (!i) {
      out = params.find(key) ? std::string("value is not a finite number") : "unknown key: " + key;
      return false;
    }
    logger.info("Param {} = {}", key, params.get(key));
    out = params.json(*i);
    return true;
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
        case PushAssistType::GetInfo:
          reply(PushAssistType::Info, bytes(info_json()));
          break;
        case PushAssistType::GetParams:
          reply(PushAssistType::Params, bytes(params.json()));
          break;
        case PushAssistType::SetParam: {
          // [key_len u8][key utf8][value f32 LE]
          const auto &p = f.payload;
          if (p.empty() || p.size() != 1u + p[0] + 4u) {
            reply_error(f.type, "SET_PARAM wants [key_len u8][key][value f32]");
            break;
          }
          const std::string key(reinterpret_cast<const char *>(p.data() + 1), p[0]);
          float value;
          std::memcpy(&value, p.data() + 1 + p[0], sizeof value);
          std::string out;
          if (set_param(key, value, out))
            reply(PushAssistType::Param, bytes(out));
          else
            reply_error(f.type, out);
          break;
        }
        case PushAssistType::SaveParams: {
          const uint8_t ok = save_params(params, logger) ? 1 : 0;
          if (ok)
            logger.info("Params saved to NVS");
          reply(PushAssistType::Saved, std::span(&ok, 1));
          break;
        }
        case PushAssistType::DefaultParams:
          params.reset_to_defaults();
          logger.info("Params back to defaults (unsaved)");
          reply(PushAssistType::Defaults, bytes(params.json()));
          break;
        default:
          reply_error(f.type, "unknown request");
          break;
        }
      },
      {.name = "Push assist",
       .app = "dashboard.html",
       .description = "Tare, device info, params",
       .protocol = "rammp.push_assist",
       .protocol_version = 1});
  if (!link.start())
    logger.error("Ethernet service failed to start");

  // --- RTPS: HandleForce to the MIB ------------------------------------------------
  // The participant binds to the interface address, so it starts (and restarts)
  // once the board has an IP; the main loop below does that. The sample task
  // publishes under rtps_mutex.
  std::mutex rtps_mutex;
  std::unique_ptr<espp::RtpsParticipant> rtps;
  std::unique_ptr<espp::Publisher<rammp::HandleForce>> force_pub;
  uint32_t force_seq = 0;

  // --- sample loop: runs at the HX711's conversion rate --------------------------
  // Both HX711s free-run at the same rate, so reading one then the other picks
  // up conversions at most one period apart.
  // CSV rows and console replies share stdout from two tasks: each goes out whole.
  std::mutex stdout_mutex;
  auto print_line = [&](const std::string &line) {
    std::lock_guard<std::mutex> lk(stdout_mutex);
    fwrite(line.data(), 1, line.size(), stdout);
    fflush(stdout);
  };
#if CONFIG_PA_CONSOLE_CSV
  const auto t0 = std::chrono::steady_clock::now();
  size_t row = 0;
#endif
  uint32_t applied_version = params.version();
  auto sample_fn = [&](std::mutex &, std::condition_variable &) {
    std::error_code ec;
    // New params from SET_PARAM / DEFAULT_PARAMS: applied here, on this task.
    if (const uint32_t v = params.version(); v != applied_version) {
      applied_version = v;
      left.set_counts_per_newton(scale());
      right.set_counts_per_newton(scale());
      left.set_invert(params.get_bool("invert_left"));
      right.set_invert(params.get_bool("invert_right"));
      left_zero.configure(zt_config());
      right_zero.configure(zt_config());
      left_gate.configure(gate_config(false));
      right_gate.configure(gate_config(true));
    }
    if (tare_requested.exchange(false)) {
      logger.info("Tare requested");
      const size_t tare_n = static_cast<size_t>(params.get("tare_samples"));
      if (left_ok)
        left_ok = left.tare(tare_n, ec);
      ec.clear();
      if (right_ok)
        right_ok = right.tare(tare_n, ec);
      ec.clear();
      left_zero.reset();
      right_zero.reset();
      left_gate.rebaseline(); // hands off now: the pads' idle readings too
      right_gate.rebaseline();
      const std::array<uint8_t, 2> done = {left_ok.load(), right_ok.load()};
      reply(PushAssistType::Tared, done);
      if (console_tare.exchange(false))
        print_line(fmt::format("PA tared [{},{}]\n", done[0], done[1]));
    }
    const bool have_left = left_ok && left.update(ec);
    ec.clear();
    const bool have_right = right_ok && right.update(ec);
    if (!have_left && !have_right) // no amp: don't spin, but keep publishing (and the probe)
      std::this_thread::sleep_for(touch_ok ? 50ms : 500ms);
    const bool tracking_on = params.get_bool("zero_tracking");
    auto track = [&](ZeroTracker &z, bool have, float n) {
      return !have ? kNan : tracking_on ? z.update(n) : n;
    };
    auto state = [](const ZeroTracker &z, bool have) {
      return !have ? kNan : z.at_limit() ? 2.0f : z.tracking() ? 1.0f : 0.0f;
    };
    const float l_ungated = track(left_zero, have_left, have_left ? left.newtons() : 0);
    const float r_ungated = track(right_zero, have_right, have_right ? right.newtons() : 0);
    const float l_raw = pad_ok[0] ? pads.read(0) : kNan;
    const float r_raw = pad_ok[1] ? pads.read(1) : kNan;
    const float l = left_gate.update(l_raw, l_ungated);
    const float r = right_gate.update(r_raw, r_ungated);

    // RTPS first: it is what the chair drives on.
    {
      uint8_t flags = 0;
      if (have_left)
        flags |= rammp::kHandleForceLeftOk;
      if (have_right)
        flags |= rammp::kHandleForceRightOk;
      if (tracking_on && have_left && left_zero.at_limit())
        flags |= rammp::kHandleForceLeftZeroAtLimit;
      if (tracking_on && have_right && right_zero.at_limit())
        flags |= rammp::kHandleForceRightZeroAtLimit;
      if (ota.session_active())
        flags |= rammp::kHandleForceUpdating;
      std::lock_guard<std::mutex> lk(rtps_mutex);
      if (force_pub)
        force_pub->publish(rammp::HandleForce{.left_n = l, .right_n = r, .flags = flags,
                                              .seq = force_seq++});
    }
    if (!have_left && !have_right && !touch_ok)
      return false;

    float board_c = kNan;
    if (tsens)
      temperature_sensor_get_celsius(tsens, &board_c);
    auto touched = [](const TouchGate &g, float raw) {
      return std::isfinite(raw) ? (g.touched() ? 1.0f : 0.0f) : kNan;
    };
    auto tare_of = [](const TouchGate &g, float raw) { return std::isfinite(raw) ? g.tare() : kNan; };
    const std::array<float, 21> values = {
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
        l_ungated,
        r_ungated,
        left_gate.percent(),
        right_gate.percent(),
        touched(left_gate, l_raw),
        touched(right_gate, r_raw),
        tare_of(left_gate, l_raw),
        tare_of(right_gate, r_raw),
        l_raw,
        r_raw,
    };
    telemetry.emit(values); // no-op until a host turns streaming on
#if CONFIG_PA_CONSOLE_CSV
    if (row++ % 100 == 0)
      print_line("time_s,left_N,right_N,sum_N,diff_N,left_counts,right_counts,left_zero_N,"
                 "right_zero_N,left_tracking,right_tracking,board_C,left_ungated_N,"
                 "right_ungated_N,left_touch_pct,right_touch_pct,left_touched,right_touched,"
                 "left_tare_N,right_tare_N,left_touch_raw,right_touch_raw\n");
    const float t = std::chrono::duration<float>(std::chrono::steady_clock::now() - t0).count();
    print_line(fmt::format(
               "{:.3f},{:.3f},{:.3f},{:.3f},{:.3f},{:.0f},{:.0f},{:.3f},{:.3f},{:.0f},{:.0f},{:.1f},"
               "{:.3f},{:.3f},{:.2f},{:.2f},{:.0f},{:.0f},{:.3f},{:.3f},{:.0f},{:.0f}\n",
               t, values[0], values[1], values[2], values[3], values[4], values[5], values[6],
               values[7], values[8], values[9], values[10], values[11], values[12], values[13],
               values[14], values[15], values[16], values[17], values[18], values[19],
               values[20]));
#endif
    return false; // keep running
  };
  auto sample_task = espp::Task::make_unique(
      {.callback = sample_fn, .task_config = {.name = "load_cells", .stack_size_bytes = 8192}});
  sample_task->start();

  // --- USB-C console commands: params without ethernet (tools/usb_board.py) -------
  // One command per line, answered with one "PA <kind> <json>" line:
  //   pa params | pa set <key> <value> | pa save | pa defaults | pa tare
  auto console_reply = [&](std::string_view kind, std::string_view body) {
    print_line(fmt::format("PA {} {}\n", kind, body));
  };
  auto console_command = [&](const std::string &line) {
    if (line == "pa params") {
      console_reply("params", params.json());
    } else if (line.rfind("pa set ", 0) == 0) {
      const auto sp = line.find(' ', 7);
      const std::string key = line.substr(7, sp == std::string::npos ? sp : sp - 7);
      char *end = nullptr;
      const float value = sp == std::string::npos ? kNan : std::strtof(line.c_str() + sp + 1, &end);
      std::string out;
      if (sp == std::string::npos || end == line.c_str() + sp + 1)
        console_reply("error", R"({"message":"pa set wants <key> <value>"})");
      else if (set_param(key, value, out))
        console_reply("param", out);
      else
        console_reply("error", fmt::format(R"({{"message":"{}"}})", out));
    } else if (line == "pa save") {
      console_reply("saved", save_params(params, logger) ? "1" : "0");
    } else if (line == "pa tare") {
      console_tare = true;
      tare_requested = true; // the sample task tares and answers "PA tared [l,r]"
    } else if (line == "pa defaults") {
      params.reset_to_defaults();
      console_reply("defaults", params.json());
    } else if (line.rfind("pa", 0) == 0) {
      console_reply("error", R"({"message":"commands: pa params | pa set <key> <value> | pa save | pa defaults | pa tare"})");
    }
  };
  const auto console_uart = static_cast<uart_port_t>(CONFIG_ESP_CONSOLE_UART_NUM);
  std::unique_ptr<espp::Task> console_task;
  if (uart_is_driver_installed(console_uart) ||
      uart_driver_install(console_uart, 1024, 0, 0, nullptr, 0) == ESP_OK) {
    uart_vfs_dev_use_driver(CONFIG_ESP_CONSOLE_UART_NUM); // stdout through the driver too
    console_task = espp::Task::make_unique(
        {.callback =
             [&, line = std::string{}](std::mutex &, std::condition_variable &) mutable {
               uint8_t buf[128];
               const int n = uart_read_bytes(console_uart, buf, sizeof buf, pdMS_TO_TICKS(100));
               for (int k = 0; k < n; k++) {
                 const char c = static_cast<char>(buf[k]);
                 if (c == '\n' || c == '\r') {
                   if (!line.empty())
                     console_command(line);
                   line.clear();
                 } else if (line.size() < 120) {
                   line += c;
                 }
               }
               return false;
             },
         .task_config = {.name = "console_rx", .stack_size_bytes = 6144}});
    console_task->start();
  } else {
    logger.warn("UART console driver did not install: no console commands");
  }

  logger.info("Running. On a laptop on the same network: python3 tools/eth_bridge.py, then "
              "open http://localhost:8765/");

  // --- main loop: RTPS up on the current IP, and the rollback gate ---------------
  std::string rtps_ip;
  auto served_since = std::chrono::steady_clock::time_point{};
  while (true) {
    std::this_thread::sleep_for(1s);
    const std::string ip = ethernet.is_connected() ? ip_string(ethernet.ip()) : std::string{};

    // (Re)start the participant when the address changes (a new lease).
    if (ip != rtps_ip) {
      std::lock_guard<std::mutex> lk(rtps_mutex);
      force_pub.reset();
      rtps.reset();
      rtps_ip = ip;
      if (!ip.empty() && ip != "0.0.0.0") {
        rtps = std::make_unique<espp::RtpsParticipant>(espp::RtpsParticipant::Config{
            .interface_address = ip, .log_level = espp::Logger::Verbosity::WARN});
        if (rtps->start()) {
          force_pub = std::make_unique<espp::Publisher<rammp::HandleForce>>(
              *rtps, espp::Publisher<rammp::HandleForce>::Config{
                         .topic = rammp::kPushAssistHandleForce.name,
                         .type_name = rammp::kPushAssistHandleForce.type});
          if (force_pub->is_valid())
            logger.info("RTPS on {}: publishing {}", ip, rammp::kPushAssistHandleForce.name);
          else {
            logger.error("RTPS publisher for {} failed", rammp::kPushAssistHandleForce.name);
            force_pub.reset();
          }
        } else {
          logger.error("RTPS participant failed to start on {}", ip);
          rtps.reset();
        }
      }
    }

    // Rollback gate: a pending image confirms itself after a lease and
    // kSelfVerifyAfter of serving. A host's MARK_VALID / MARK_INVALID wins.
    if (booted_pending && ota.is_pending_verify()) {
      if (ip.empty())
        served_since = {};
      else if (served_since == std::chrono::steady_clock::time_point{})
        served_since = std::chrono::steady_clock::now();
      else if (std::chrono::steady_clock::now() - served_since >= kSelfVerifyAfter) {
        std::error_code ec;
        if (ota.mark_app_valid(ec))
          logger.info("Image self-confirmed: lease held and service up for {} s",
                      std::chrono::duration_cast<std::chrono::seconds>(kSelfVerifyAfter).count());
        else
          logger.error("Self-confirm failed: {}", ec.message());
      }
    }
  }
}
