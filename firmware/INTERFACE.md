# Push-assist board: network interface

What the push-assist board serves. Write against this whether you're the MIB, the MIB
control panel or the dashboard in this repo. The code behind it is `main/main.cpp`,
`main/eth_link.hpp` and `main/params.hpp`. The MIB's side of driving from the handles is in
[`docs/MIB-INPUT-DEVICES.md`](../docs/MIB-INPUT-DEVICES.md).

Status, 2026-11-02:
- OTA, the params module, the extra GET_INFO fields and the RTPS `HandleForce` publisher
  are built and compile.
- On the host: the params table is unit-tested, the dashboard and `tools/check_service.py`
  pass against `tools/mock_board.py`, and `tools/rtps_listen.py` receives `HandleForce`
  from a Cyclone DDS publisher.
- **Not yet run on the board.** The bench test (OTA and rollback, params through NVS,
  `HandleForce` received by an independent DDS reader) is next.
- The OTA, params and GET_INFO spec was agreed with the MIB control-panel session
  (RAMMP-mib-fw, `tools/mib_panel/`). Alex: "It will need to be able to flash OTA just like
  everything else on the system, and it will need to coordinate settings for the MIB and
  maybe the space bar module itself."

## Board and network

- **Board:** Waveshare ESP32-P4-WIFI6-POE-ETH. The bench board is P4 silicon v3.2, and the
  build targets v3.x.
- **Sensors:** two SparkFun HX711 load-cell amps. Left: CLK GPIO 21, DAT GPIO 20. Right:
  CLK GPIO 5, DAT GPIO 4.
- **Ethernet:** RMII PHY on the board, PoE capable. The default build is a **DHCP client**:
  on the chair it takes its lease from the MIB, on the chair's switch.
- **Bench build** (`sdkconfig.bench`): the board is the DHCP server at **192.168.4.1/24**,
  for a laptop plugged straight in. Never use it on the chair's network: it would fight
  the MIB's DHCP.
- **Console:** UART0 on the USB-C (CH343P, 115200). The first flash goes over this; after
  that, OTA works over ethernet.

## To the MIB: RTPS

| | |
|---|---|
| Topic | `rammp/push_assist/handle_force` (`rammp::kPushAssistHandleForce`) |
| Type | `rammp/msg/HandleForce`, from rammp-rtps `messages/push_assist_message.hpp` ([PR #23](https://github.com/rammp-org/rammp-rtps/pull/23); this firmware pins it as the `external/rammp-rtps` submodule) |
| QoS | Best-effort, domain 0 |
| Rate | One sample per conversion: 10 Hz now, 80 Hz with the HX711 RATE pin high and `PA_HX711_80SPS` |
| Participant | Starts once the board has an IP, and restarts on a new lease |

```cpp
struct HandleForce {
  float left_n;   // N, push +, tared and zero-tracked; NaN while the left amp is not answering
  float right_n;  // N, same for the right handle
  uint8_t flags;  // kHandleForceLeftOk | RightOk | LeftZeroAtLimit | RightZeroAtLimit | Updating
  uint32_t seq;   // +1 per sample since boot
};
```

- **Raw handle forces, never a twist:** the MIB shapes them. A handle is usable only while
  its OK bit is set and its ZERO_AT_LIMIT bit is clear. `Updating` is set while an OTA
  session is open.
- **No amps:** the board keeps publishing even with no amp answering (NaN, flags clear), so
  the MIB sees a live but unusable device, not silence.

## Service stream

The same framing as the PACE RACER: espp `stream_frame` v2, routed by an
`espp::DispatcherWorker`.

| | |
|---|---|
| TCP | **:5555**, one client at a time. A new client replaces the old one, so the panel, this repo's dashboard and its tools take turns. |
| UDP | **:5556**. The board answers `PUSH?` (not `PACE?`) with the GET_INFO JSON, unicast to the asker. |

| Module | What |
|---|---|
| 0 | espp `OtaService` (`espp.ota` v1), with a rollback gate (below) |
| 3 | `espp::Telemetry` (`espp.telemetry` v1): GET_SCHEMA `0x01`, SET_STREAM `0x02` `[enabled u8][period_ms u16]`, SCHEMA `0x81`, SAMPLE `0x82`. Streams once a client sends SET_STREAM; stops when the client goes. |
| 0x30 | `push_assist` (`rammp.push_assist` v1): tare, info, params (below) |
| 0xFF | espp dispatcher discovery: device name "Push Assist", firmware = app version |

The board serves no console (0x10) or system (0x20) module; info comes from 0x30 GET_INFO.

### OTA, module 0

- **Service:** espp `OtaService`, as on the PACE RACER.
- **Flow:** BEGIN `[size]`, then 4 KiB DATA frames, then FINISH. The board reboots into the
  new image. GET_STATUS, MARK_VALID, MARK_INVALID and ABORT also work.
- **Image check:** the image's `esp_app_desc` `project_name` is `push_assist`.
- **Rollback gate:** a new image boots PENDING_VERIFY. A host's MARK_VALID confirms it at
  once. Otherwise it confirms itself once it holds a lease and has served for **20 s**. A
  reset before either rolls back to the previous image.
- **Partitions:** `ota_0` and `ota_1` (1920 KiB each), `otadata`, `coredump`.
- **From a laptop:** `tools/ota_eth.py --ip <board> flash build/push_assist.bin`, which
  checks GET_INFO before and after and marks the image valid.

### push_assist, module 0x30

Requests are `0x0X`; replies are `0x8X` with the reply flag set.

| Request | Reply |
|---|---|
| `0x01` TARE: re-zero both cells (handles unloaded); also clears zero tracking. About 1.6 s at 10 S/s. | `0x81` `[left_ok u8][right_ok u8]` |
| `0x02` GET_INFO | `0x82` INFO JSON, below |
| `0x03` GET_PARAMS | `0x83` `{"params":[...]}` |
| `0x04` SET_PARAM `[key_len u8][key utf8][value f32 LE]` | `0x84`: that param's object after apply (clamped). Takes effect at once, in RAM only. |
| `0x05` SAVE_PARAMS | `0x85` `[ok u8]`: committed to NVS, loaded at boot |
| `0x06` DEFAULT_PARAMS | `0x86` `{"params":[...]}`, back to the Kconfig defaults in RAM (unsaved) |
| a malformed or unknown request, or an unknown key | `0x8F` `[request type u8][utf8 message]` |

INFO JSON (the `PUSH?` reply is the same object):

```json
{"product":"push_assist","project":"push_assist","firmware":"<app version>",
 "built":"Nov  2 2026 12:00:00","partition":"ota_0","pending_verify":false,
 "ip":"192.168.4.1","left":true,"right":true,"counts_per_N":10949.12,
 "full_scale_kg":20,"rated_uV_per_V":1000,"sps":10,
 "pins":{"left_dat":20,"left_clk":21,"right_dat":4,"right_clk":5},
 "invert":{"left":false,"right":false},"zero_tracking":true}
```

- `left` and `right` are false when that amp did not answer at boot.
- `invert`, `zero_tracking` and the scale fields follow the current params.

### Params

Each param is self-describing; the panel renders whatever the board lists:

```json
{"key":"zt_band_n","label":"Zero-track band","unit":"N","value":2,"default":2,
 "min":0,"max":20,"step":0.1,"group":"Zero tracking"}
```

- A bool has `"type":"bool"` and value 0 or 1, and no unit, min, max or step.
- Values are in the unit shown (N, not the Kconfig's mN).
- The Kconfig values are the defaults; values saved to NVS (namespace `push_assist`, one
  u32 per key) override them at boot.

| Key | Unit | Default | Range | Group |
|---|---|---|---|---|
| `invert_left`, `invert_right` | bool | 0 | | Cells |
| `full_scale_kg` | kg | 20 | 1..500 | Cells |
| `rated_uv_per_v` | µV/V | 1000 | 100..5000 | Cells |
| `tare_samples` | readings | 16 | 1..255 | Cells |
| `zero_tracking` | bool | 1 | | Zero tracking |
| `zt_band_n` | N | 2.0 | 0..20 | Zero tracking |
| `zt_still_std_n` | N | 0.05 | 0..1 | Zero tracking |
| `zt_rate_n_per_s` | N/s | 0.005 | 0..0.1 | Zero tracking |
| `zt_max_n` | N | 10 | 0..100 | Zero tracking |

- **Takes effect:** a change applies on the next sample. The scale and invert change the
  reading at once; the zero-tracking settings keep the correction made so far. Tare
  samples apply to the next tare.
- **Compile-time only:** the pins, `PA_HX711_80SPS`, `PA_ETH_DHCP_SERVER` and
  `PA_CONSOLE_CSV`.

**MIB-side params** (the driving decisions, per `docs/MIB-INPUT-DEVICES.md`) live on the
MIB, on its control module (0x40) with the same self-describing protocol:

| Param | Unit | Start |
|---|---|---|
| `dead_band_n` | N per handle | 10 |
| `forward_full_n` | N | 60 |
| `turn_full_n` | N | 30 |
| `reverse_max` | 0..1 | 0.3 |
| push-assist planner limits | | the LOW profile (0.35 m/s, 1 rad/s) |

## Telemetry channels (module 3)

In SCHEMA order, all f32. Each SAMPLE record is `[timestamp_us u32][11 × f32]`.

| Channel | Unit | Meaning |
|---|---|---|
| `left_N`, `right_N` | N | Handle force, push +, tared and zero-tracked. NaN if the amp is not answering |
| `sum_N` | N | left + right: forward |
| `diff_N` | N | left − right: + is a clockwise (right) turn from above |
| `left_counts`, `right_counts` | counts | Tared HX711 counts (10949 counts/N nominal) |
| `left_zero_N`, `right_zero_N` | N | Correction zero tracking has taken out since the last tare |
| `left_tracking`, `right_tracking` | 0/1/2 | 0 idle, 1 moving the zero, 2 at its cap (tare needed) |
| `board_C` | °C | P4 die temperature |

- **For tuning:** plot `left_N`, `right_N`, `sum_N` and `diff_N`.
- **For drift:** plot `*_zero_N` against `board_C`.
- **The MIB's view:** `pushToTwist()` in `web/dashboard.html` is the reference conversion,
  and the dashboard shows the command it would give.

## Tools (`tools/`)

| Tool | What |
|---|---|
| `eth_bridge.py` | Serves `web/dashboard.html` and relays a WebSocket to tcp :5555; `--list` runs discovery |
| `ota_eth.py` | Flash over ethernet: `flash`, `status`, `mark-valid`, `rollback` |
| `check_service.py` | Exercises GET_INFO and the params protocol; `--save` adds the NVS round trip. Leaves params as it found them |
| `rtps_listen.py` | Subscribes to `HandleForce` over RTPS with Cyclone DDS (`pip install cyclonedds`, Python 3.10-3.12) |
| `log_forces.py` | Logs the telemetry to CSV for long runs |
| `mock_board.py` | Stand-in board: telemetry, tare, info and params, for work without hardware. No OTA. |
