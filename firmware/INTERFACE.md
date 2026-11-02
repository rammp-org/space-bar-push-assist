# Push-assist board: network interface

What the push-assist board serves today, and what is proposed but not built. It is for
anything that talks to the board: the MIB, the MIB control panel, this repo's dashboard.
Source of truth for the code: `main/main.cpp` and `main/eth_link.hpp` (main, `88f89ee`,
2026-11-02). The MIB side is in [`docs/MIB-INPUT-DEVICES.md`](../docs/MIB-INPUT-DEVICES.md).

## Board and network

- **Board:** Waveshare ESP32-P4-WIFI6-POE-ETH. The bench board is ESP32-P4 silicon v3.2, and
  the build targets v3.x.
- **Sensors:** two SparkFun HX711 load-cell amps, one per handle. Left: CLK GPIO 21, DAT
  GPIO 20. Right: CLK GPIO 5, DAT GPIO 4.
- **Ethernet:** RMII PHY on the board, PoE capable. The default build is a **DHCP client**:
  on the chair it takes its lease from the MIB, on the chair's switch.
- **Bench build** (`sdkconfig.bench`): the board is the DHCP server at **192.168.4.1/24**,
  for a laptop plugged straight in. Never on the chair's network: it would fight the MIB's
  DHCP.
- **Console:** UART0 on the USB-C (CH343P, 115200). This is also how it is flashed today.

## What it sends the MIB

**Nothing yet.** There is no RTPS on the board, and no push-assist message in rammp-rtps.

What it will send, proposed in `docs/MIB-INPUT-DEVICES.md`:
- **Raw handle forces, not a twist.** The MIB does all the shaping. Two forces in N (push
  +), plus health flags and a sequence number.
- **Message:** `HandleForce` on `rammp/push_assist/handle_force`.
- **Rate:** the load cells' rate, 10 S/s now (80 S/s with the HX711 RATE pin high and
  `PA_HX711_80SPS`).
- **Already in rammp-rtps:** `MibSystemState::PUSH_ASSIST` and `DriveCommand.push_assist`.

## Service stream (built)

The same framing as the PACE RACER: espp `stream_frame` v2, routed by an
`espp::DispatcherWorker`. The module set is smaller, though.

| | |
|---|---|
| TCP | **:5555**, one client at a time. A new client replaces the old one, so the panel, this repo's dashboard and `tools/log_forces.py` take turns. |
| UDP | **:5556**. The board answers `PUSH?` (not `PACE?`) with one JSON line, unicast to the asker. |

| Module | What | Status |
|---|---|---|
| 3 | `espp::Telemetry` (`espp.telemetry` v1): GET_SCHEMA `0x01`, SET_STREAM `0x02` `[enabled u8][period_ms u16]`, SCHEMA `0x81`, SAMPLE `0x82`. Streams once a client sends SET_STREAM; stops when the client goes. | built |
| 0x30 | `push_assist` (`rammp.push_assist` v1): see below | built |
| 0xFF | espp dispatcher discovery: device name "Push Assist", firmware = app version | built |
| 0 | espp `OtaService` | **not built** (proposed below) |
| 0x10 | console / log | **not built** |
| 0x20 | system (reset, info) | **not built**: GET_INFO on 0x30 covers info |

Module 0x30 `push_assist`: requests are `0x0X`, replies `0x8X` with the reply flag set.

| Request | Reply |
|---|---|
| `0x01` TARE: re-zero both cells (handles unloaded); also clears zero tracking. About 1.6 s at 10 S/s. | `0x81` TARED `[left_ok u8][right_ok u8]` |
| `0x02` GET_INFO | `0x82` INFO: UTF-8 JSON, below |

INFO JSON (the UDP discovery reply is the same object):

```json
{"product":"push_assist","firmware":"<app version>","ip":"192.168.4.1",
 "left":true,"right":true,"counts_per_N":10949.12,"full_scale_kg":20,
 "rated_uV_per_V":1000,"sps":10,
 "pins":{"left_dat":20,"left_clk":21,"right_dat":4,"right_clk":5},
 "invert":{"left":false,"right":false},"zero_tracking":true}
```

`left` and `right` are false when that amp did not answer at boot.

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

For tuning, plot `left_N`, `right_N`, `sum_N` and `diff_N`; for drift, plot `*_zero_N`
against `board_C`. The board's own reference conversion to a drive command,
`pushToTwist()` in `web/dashboard.html`, shows what the MIB would command from these.

## Parameters

**Device side: compile-time Kconfig only today** (`main/Kconfig.projbuild`, menu "Push
assist"). No NVS, and nothing settable at runtime except TARE.

| Kconfig | Unit | Default | Range |
|---|---|---|---|
| `PA_LEFT_DOUT_GPIO` / `PA_LEFT_SCK_GPIO` | GPIO | 20 / 21 | 0..54 |
| `PA_RIGHT_DOUT_GPIO` / `PA_RIGHT_SCK_GPIO` | GPIO | 4 / 5 | 0..54 |
| `PA_LEFT_INVERT`, `PA_RIGHT_INVERT` | bool | n | |
| `PA_CELL_FULL_SCALE_KG` | kg | 20 | 1..500 |
| `PA_CELL_RATED_UV_PER_V` | µV/V | 1000 | 100..5000 |
| `PA_HX711_80SPS` | bool | n (10 S/s) | must match the amp's RATE pin |
| `PA_TARE_SAMPLES` | readings | 16 | 1..255 |
| `PA_ZERO_TRACKING` | bool | y | |
| `PA_ZT_BAND_MN` | mN | 2000 | track only below this |
| `PA_ZT_STILL_STD_MN` | mN | 50 | still if the 2 s std is below this |
| `PA_ZT_RATE_UN_PER_S` | µN/s | 5000 | max zero rate |
| `PA_ZT_MAX_N` | N | 10 | max total correction since tare |
| `PA_ETH_DHCP_SERVER` | bool | n | y only in `sdkconfig.bench` |
| `PA_CONSOLE_CSV` | bool | y | CSV rows on the console |

**MIB side** (driving decisions, per `docs/MIB-INPUT-DEVICES.md`). These are only in the
dashboard's `pushToTwist()` so far:

| Parameter | Unit | Start |
|---|---|---|
| `dead_band_n` | N per handle | 10 (or max(10, 280 × \|c\| × 1.2) from the bench crosstalk) |
| `forward_full_n` | N | 60 |
| `turn_full_n` | N | 30 |
| `reverse_max` | 0..1 | 0.3 |
| push-assist planner profile | | LOW (0.35 m/s, 1 rad/s) |
| lapse timeout | ms | 300 |

## Agreed with the MIB panel, not built yet

Spec from the MIB control-panel session (RAMMP-mib-fw, `tools/mib_panel/`), 2026-11-02.
Alex's requirement: "It will need to be able to flash OTA just like everything else on the
system, and it will need to coordinate settings for the MIB and maybe the space bar module
itself." Not built until Alex gives the go-ahead in this repo.

### OTA, module 0

- **Service:** espp `OtaService`, exactly as the PACE RACER serves it.
- **Panel flow:** BEGIN `[size]`, then 4 KiB DATA frames, then FINISH. The board
  reboots, the panel reconnects and sends MARK_VALID. GET_STATUS, MARK_INVALID and ABORT
  are also used.
- **Rollback gate (RACER's):** a new image boots PENDING_VERIFY and confirms itself only
  after it holds a lease and has served the stream for 20 s. If it never gets there, the
  next reset falls back to the previous image.
- **Image check:** the panel reads the image's `esp_app_desc` `project_name` and expects
  `push_assist`. That is the CMake project name; keep it.
- **Partitions:** already OTA-ready (`ota_0`, `ota_1`, `otadata`, `coredump`).

### GET_INFO additions

The 0x30/0x02 reply and the `PUSH?` reply gain these fields:

| Field | Value |
|---|---|
| `project` | `"push_assist"` (`esp_app_desc` project_name) |
| `built` | `"<date> <time>"` (`esp_app_desc` date and time) |
| `partition` | `"ota_0"` or `"ota_1"`: the running partition |
| `pending_verify` | `true` while the running image is not yet confirmed |

The pins and the RATE flag stay compile-time and are reported in GET_INFO only.

### Params, module 0x30, self-describing

The panel renders whatever the board lists, so params can be added later without a panel
change. The same protocol runs on the MIB control module (0x40) for the MIB-side
push-assist gains, so the panel shows both with one renderer.

| Request | Reply |
|---|---|
| `0x03` GET_PARAMS | `0x83`: UTF-8 JSON `{"params":[...]}`, one object per param (below) |
| `0x04` SET_PARAM `[key_len u8][key utf8][value f32]` | `0x84`: that param's JSON object after apply (clamped). Takes effect at once, in RAM only |
| `0x05` SAVE_PARAMS | `0x85` `[ok u8]`: committed to NVS, loaded at boot |
| `0x06` DEFAULT_PARAMS | `0x86`: the GET_PARAMS JSON, back to the Kconfig defaults in RAM (unsaved) |
| any failure | `0x8F` `[request type u8][utf8 message]`, as on the MIB's control module |

A param object:

```json
{"key":"zt_band_n","label":"Zero-track band","unit":"N","value":2.0,"default":2.0,
 "min":0,"max":20,"step":0.1,"group":"Zero tracking"}
```

Rules:
- Keys are snake_case, and values are in the unit shown (N, not the Kconfig's mN).
- A bool has `"type":"bool"` and value 0 or 1.
- Kconfig values are the defaults; NVS overrides them at boot.

Candidate params, built from the current Kconfig:

| Key | Unit | Default | Group |
|---|---|---|---|
| `invert_left`, `invert_right` | bool | 0 | Cells |
| `full_scale_kg` | kg | 20 | Cells |
| `rated_uv_per_v` | µV/V | 1000 | Cells |
| `tare_samples` | readings | 16 | Cells |
| `zero_tracking` | bool | 1 | Zero tracking |
| `zt_band_n` | N | 2.0 | Zero tracking |
| `zt_still_std_n` | N | 0.05 | Zero tracking |
| `zt_rate_n_per_s` | N/s | 0.005 | Zero tracking |
| `zt_max_n` | N | 10 | Zero tracking |

### Not needed

The panel doesn't use console (0x10) or system (0x20); it takes info from 0x30 GET_INFO.

### Also planned

RTPS `HandleForce` to the MIB, per `docs/MIB-INPUT-DEVICES.md`.
