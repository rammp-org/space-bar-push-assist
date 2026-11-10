# Push-assist firmware

ESP-IDF + [espp](https://github.com/esp-cpp/espp) app for the Waveshare
ESP32-P4-WIFI6-POE-ETH. It reads one load cell per handle through two SparkFun HX711
breakouts. It publishes the forces to the MIB over RTPS (`rammp::HandleForce`), and serves a
live HTML dashboard, runtime params and OTA updates over ethernet. Everything on the wire
is in [`INTERFACE.md`](INTERFACE.md).

| Path | What |
|---|---|
| `main/` | The app: `main.cpp`, `load_cell.hpp` (HX711 wrapper), `zero_tracker.hpp`, `params.hpp` (runtime params), `eth_link.hpp` (ethernet service) |
| `web/dashboard.html` | Live dashboard: handle forces, forward and turn, tare, CSV export, board settings |
| `web/ax/` | alex-style assets (`tokens.css`, `ax-fx.js`, `ax-charts.js`), copied from alex-style-guide |
| `tools/eth_bridge.py` | Serves the dashboard on http://localhost:8765/ and relays its WebSocket to the board |
| `tools/mock_board.py` | A stand-in board speaking the same protocol, for dashboard work without hardware |
| `tools/usb_board.py` | The board over its USB-C console instead of ethernet: reads the console CSV and serves it to the dashboard (connect to 127.0.0.1). Params and tare go to the board as console commands (INTERFACE.md). `--csv` logs every row |
| `INTERFACE.md` | The board's network interface: RTPS, service stream, discovery, OTA, params, telemetry channels |
| `tools/ota_eth.py` | Flash over ethernet (espp OTA): `flash`, `status`, `mark-valid`, `rollback` |
| `tools/check_service.py` | Exercises GET_INFO and the params protocol against the board or the mock |
| `tools/rtps_listen.py` | Subscribes to the board's `HandleForce` over RTPS (Cyclone DDS), as the MIB will |
| `external/rammp-rtps` | Submodule: the shared RTPS messages (`HandleForce`). `git submodule update --init` before building |
| `tools/log_forces.py` | Logs the telemetry to CSV for long runs (drift, creep), one summary line a minute |

How the MIB should take these forces, the reference push-to-drive conversion
(`pushToTwist()` in `web/dashboard.html`) and what each repo still needs:
[`docs/MIB-INPUT-DEVICES.md`](../docs/MIB-INPUT-DEVICES.md).

## How it works

- **To the MIB:** `rammp::HandleForce` over RTPS on `rammp/push_assist/handle_force`, one
  sample per conversion: the two handle forces in N, health flags and a sequence number.
  The MIB turns them into drive commands.
- **Service stream:** the same pattern as PACE RACER's ethernet tools. The board serves an
  espp `stream_frame` byte stream on **tcp :5555** and answers `PUSH?` on **udp :5556**.
  The stream carries OTA (module 0), telemetry (3), and push_assist (0x30: tare, info,
  params).
- **Dashboard:** a browser can't open raw TCP, so `tools/eth_bridge.py` (Python standard
  library, nothing to install) serves the page and relays a WebSocket to the board. The page
  does all the protocol work.

Module, channel and param details are in [`INTERFACE.md`](INTERFACE.md).

| Channel | Meaning |
|---|---|
| `left_N`, `right_N` | Force on each handle in newtons, push + |
| `sum_N` | left + right: forward force |
| `diff_N` | left − right: + is a clockwise (right) turn seen from above, as `rammp::XYTwist::twist` |
| `left_counts`, `right_counts` | Tared HX711 counts, push + |
| `left_zero_N`, `right_zero_N` | Zero tracking's correction, already taken out of `*_N` |
| `left_tracking`, `right_tracking` | 0 idle, 1 moving the zero, 2 at its cap (tare to reset) |
| `board_C` | P4 die temperature, °C |

If a handle's HX711 doesn't answer at boot, it streams NaN and the dashboard shows "No
amp". That lets you bring up one amp on its own. The same rows also go to the UART0
console on the USB-C as CSV (`PA_CONSOLE_CSV`).

## Wiring

SparkFun HX711 breakout to the 40-pin header (GPIOs set in `idf.py menuconfig` →
*Push assist*):

| HX711 pin | Left amp | Right amp |
|---|---|---|
| CLK | GPIO 5 | GPIO 21 |
| DAT | GPIO 4 | GPIO 20 |
| VCC, VDD | 3V3 | 3V3 |
| GND | GND | GND |

Touch pads (INTERFACE.md, "Touch switch and tare"): one wire per handle, from the
header pin straight into the grip; no resistor, no ground to the pad. Keep the lead short
and away from the HX711 wires: it is part of the pad.

| Pad | GPIO |
|---|---|
| Left handle | 3 |
| Right handle | 2 |

Pins to avoid:
- **GPIO 37 / 38:** UART0, the USB-C console. The CH343P drives GPIO 38, so an amp there
  never reports a conversion while the USB-C is plugged in. The firmware warns at boot if
  an amp is set there.
- **GPIO 7 / 8:** the internal I2C bus (ES8311 codec, pull-ups). It works only while
  nothing starts I2C there, which is one reason `main.cpp` drives `espp::Ethernet` itself
  rather than through the BSP singleton (that singleton starts the bus when it is
  constructed).

Cell to amp: red E+, black E−, white A−, green A+ (check the cell's label). The HX711
converts at 10 samples/s with its RATE pin low and 80 with RATE high. That is set by the
board, not the firmware: if your breakout has RATE high, set `PA_HX711_80SPS`.

## Build and flash

```sh
git submodule update --init   # external/rammp-rtps: the RTPS messages
. ~/esp/esp-idf/export.sh     # ESP-IDF 6.0
cd firmware
idf.py build
idf.py -p <USB-C port> flash monitor   # first flash: CH343P USB-UART; auto reset/boot
python3 tools/ota_eth.py --ip <board> flash build/push_assist.bin   # after that, over ethernet
```

`ota_eth.py flash` checks the running image, sends the new one, waits for the board to
come back and marks it valid. A new image that nobody confirms confirms itself after a
lease and 20 s of service; a reset before that rolls it back.

Bench build (board is the DHCP server, see Network):

```sh
idf.py -B build-bench -D SDKCONFIG=build-bench/sdkconfig \
       -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.bench" -p <USB-C port> build flash
```

The build targets ESP32-P4 silicon v3.x (the bench board reads v3.2). A v1.x board needs
`CONFIG_ESP32P4_SELECTS_REV_LESS_V3=y`.

The espp and HX711 components come from the ESP component registry on the first build.

## Network

- **On the chair:** the board takes a DHCP lease from the MIB (the default).
- **On the bench, laptop cable straight into the board:** use the bench build above
  (`sdkconfig.bench` sets `PA_ETH_DHCP_SERVER`). The board takes 192.168.4.1 and leases the laptop an address.
  Never use this on the chair's network.
- **On the bench, through a switch with no DHCP server:** PACE RACER's
  `tools/mock_mib_dhcp.py` (pace-racer-fw, atos-drive) works here too.

## Dashboard

```sh
python3 tools/eth_bridge.py            # then open http://localhost:8765/
```

The page asks the LAN who's there when it loads. **Find boards** asks again, or you can
type the board's IP (the console logs it at boot). Then press **Connect**. Before taring,
make sure both handles are unloaded; the firmware also tares at boot.
`python3 tools/eth_bridge.py --list` runs the same lookup in a terminal.

Without hardware: run `python3 tools/mock_board.py` (`--no-right` to fake a missing amp,
`--sps 80`) next to the bridge and connect to `127.0.0.1`.

If Find boards finds nothing:
- Check the laptop's ethernet adapter has an address on the board's subnet.
- Check that a firewall isn't dropping the UDP reply to :5556 (macOS asks once for
  Python).
- Check that Tailscale isn't claiming the range.

Typing the IP skips discovery.

## Zero drift and zero tracking

An assembled handle's zero drifts as the clamp load on its cell relaxes in the
printed cartridge. The clamp needs that load, or the joint has slop.

Bench, 2026-10-28, 1-hour log (`tools/log_forces.py`):
- The assembled left handle drifted −5.76 N, a nearly steady −0.096 N/min that slowed
  only about 10 % over the hour.
- The loose right cell moved +0.03 N.
- Board temperature stayed at 33.6–34.6 °C.

Clamp creep should slow down much more than that, so the left cell or its amp is not
ruled out. That channel also had a 1.4M-count zero offset at boot. Open: swap the two
cells between amps and see whether the drift follows the cell.

`main/zero_tracker.hpp` follows the drift the way scales do. While a handle reads under
2 N and holds still (2 s std under 0.05 N, for 5 s), it walks that handle's zero toward
the reading at up to 0.005 N/s. That is about 7× the bench drift rate. The total
correction since the last tare is capped at 10 N; at the cap, the dashboard asks for a
tare. Settings are under *Push assist* in menuconfig (`PA_ZERO_TRACKING`, `PA_ZT_*`).

Host simulation of the defaults:

| Case | Result |
|---|---|
| Drift of 0.0007 N/s for 1 h, and 3× that | Held within 0.02 N |
| A hand resting at 1.5 N, with normal tremor | Not tracked: tremor is well over 0.05 N |
| A push | Not tracked |
| A perfectly still 1.5 N load, such as a bag hung on a handle | Erased at 0.005 N/s: 0.56 N in 2 min. This is the trade-off. |

On the board, with tracking on (23.5 min, stopped early): the left reading stayed within
0.016 N while the tracker took out −1.87 N; the right stayed within 0.014 N. At this
drift the left reaches the 10 N cap about 1 h 50 min after a tare.

The dashboard shows each handle's correction and when tracking is active.
`tools/log_forces.py` logs long runs to CSV, with one summary line a minute.

## Scale

Counts per newton come from the cell's full scale and rated output
(`PA_CELL_FULL_SCALE_KG`, default 20; `PA_CELL_RATED_UV_PER_V`, default 1000 = 1.0 mV/V).
The HX711 at gain 128 is ratiometric when the bridge is excited from its own AVDD, as on
the SparkFun breakout: counts per V/V = 128 × 2²⁴. So the scale needs no calibration
mass, but it's only as good as the label. The README's known-mass check (stop setting,
step 4) catches a wrong label.

## Why not the existing code

- **Touch pads:** espp has no capacitive-touch wrapper; ESP-IDF's
  `esp_driver_touch_sens` is used as its `touch_sens_basic` example sets it up
  (`main/touch_probe.hpp`). Its own benchmark and active flag were tried first and
  dropped: the benchmark froze when the probe was attached and the flag stayed on for the
  whole bench run (100 % of 1338 samples), so `main/touch_gate.hpp` keeps the baseline.

- **HX711 driver:** espp has none. The registry's
  [`esp-idf-lib/hx711`](https://components.espressif.com/components/esp-idf-lib/hx711)
  supports the ESP32-P4. It clocks the 25 bits inside a critical section, so PD_SCK never
  stays high past the HX711's 60 µs power-down limit. That's the part that's easy to get
  wrong, so it's used as is. `main/load_cell.hpp` adds tare, sign and newtons. It also
  works around one gap in the driver: `hx711_init()` waits only 200 ms for the first
  conversion, but an HX711 at 10 S/s needs about 400 ms after power-up. On the board, amp 1
  timed out with the stock wait and came up once init waited 1 s.
- **Ethernet and dashboard:** PACE RACER already serves the espp framed stream over TCP
  with UDP discovery, and has a stdlib WebSocket bridge for an HTML page.
  `main/eth_link.hpp` and `tools/eth_bridge.py` are those files, cut down: no OTA,
  console, rollback gate or build list. The board side uses the espp
  `esp32-p4-wifi6-poe-eth` BSP for Ethernet and `espp::Telemetry` for the channels.
- **Plotting:** the dashboard uses alex-style's `ax-charts.js`. espp's hosted Serial
  Plotter can't be used here, because it only speaks WebUSB and Web Serial and has no
  ethernet path. An earlier version streamed over WebUSB instead, but this board's USB-A
  jack always puts out 5 V, so it needed a special cable.

Tested on 2026-10-28 without hardware: the dashboard ran in headless Chrome through the
bridge against `tools/mock_board.py` at 10 and 80 S/s, with and without the right amp.
Connect, live plots, tare and the missing-amp states all worked. The Python, JavaScript
and espp C++ frame encoders give identical bytes.

On the board, 2026-10-28 (v3.2 silicon, bench build, MacBook on `en7`):
- The board leased the Mac 192.168.4.2, and `--list` found it.
- First wiring: amp 1 on GPIO 7/8 streamed over tcp :5555; amp 2 on GPIO 37/38 never
  answered (the UART conflict above).
- Rewired to the pins in the table: both amps come up, at 11.0 S/s over 10 s. Unloaded
  after the boot tare: left −0.018 N, right +0.006 N, both with a noise std of 0.003 N.
