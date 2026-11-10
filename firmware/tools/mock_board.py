#!/usr/bin/env python3
"""Stand-in for the push-assist board, for working on the dashboard without
hardware. Speaks the firmware's protocol on tcp :5555 (espp stream_frame v2:
telemetry on module 3, push_assist on module 0x30) and answers "PUSH?" on
udp :5556.

    python3 tools/mock_board.py              # then: tools/eth_bridge.py, connect to 127.0.0.1
    python3 tools/mock_board.py --no-right   # the right amp "not wired": NaN, as the firmware does

The forces are made up: a slow push on both handles with a turn wobble.
Standard library only.
"""
import argparse
import json
import math
import random
import socket
import struct
import threading
import time
import zlib

CHANNELS = ["left_N", "right_N", "sum_N", "diff_N", "left_counts", "right_counts",
            "left_zero_N", "right_zero_N", "left_tracking", "right_tracking", "board_C",
            "left_ungated_N", "right_ungated_N", "left_touch_pct", "right_touch_pct",
            "left_touched", "right_touched", "left_tare_N", "right_tare_N",
            "left_touch_raw", "right_touch_raw"]
TELEMETRY, PUSH = 3, 0x30
COUNTS_PER_N = 10949.1  # 20 kg cell at 1.0 mV/V, as the firmware's nominal scale

# The firmware's params (main.cpp param_defs()), with the Kconfig defaults.
PARAM_DEFS = [
    dict(key="invert_left", label="Invert left cell", group="Cells", type="bool", default=0),
    dict(key="invert_right", label="Invert right cell", group="Cells", type="bool", default=0),
    dict(key="full_scale_kg", label="Cell full scale", unit="kg", group="Cells", default=20, min=1, max=500, step=1),
    dict(key="rated_uv_per_v", label="Cell rated output", unit="uV/V", group="Cells", default=1000, min=100, max=5000, step=1),
    dict(key="tare_samples", label="Tare readings", unit="readings", group="Cells", default=16, min=1, max=255, step=1),
    dict(key="zero_tracking", label="Zero tracking", group="Zero tracking", type="bool", default=1),
    dict(key="zt_band_n", label="Zero-track band", unit="N", group="Zero tracking", default=2.0, min=0, max=20, step=0.1),
    dict(key="zt_still_std_n", label="Still below (2 s std)", unit="N", group="Zero tracking", default=0.05, min=0, max=1, step=0.005),
    dict(key="zt_rate_n_per_s", label="Max zero rate", unit="N/s", group="Zero tracking", default=0.005, min=0, max=0.1, step=0.0005),
    dict(key="zt_max_n", label="Max correction since tare", unit="N", group="Zero tracking", default=10, min=0, max=100, step=1),
    dict(key="touch_gate", label="Touch switch and tare", group="Touch", type="bool", default=1),
    dict(key="touch_l_on_pct", label="Left touched above", unit="%", group="Touch", default=8.0, min=0.5, max=50, step=0.1),
    dict(key="touch_l_off_pct", label="Left released below", unit="%", group="Touch", default=4.0, min=0.2, max=50, step=0.1),
    dict(key="touch_r_on_pct", label="Right touched above", unit="%", group="Touch", default=3.0, min=0.5, max=50, step=0.1),
    dict(key="touch_r_off_pct", label="Right released below", unit="%", group="Touch", default=1.5, min=0.2, max=50, step=0.1),
]
SAVED = {}  # what SAVE_PARAMS committed ("NVS"), kept across connections


def frame(module, ftype, payload=b"", reply=True):
    hdr = struct.pack("<HBBBI", 0x4F54, 0x10 | (1 if reply else 0), module, ftype, len(payload))
    body = hdr + payload
    return body + struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF)


def parse(buf):
    """-> (frames, rest). Resyncs past bad magic or CRC, like espp's StreamParser."""
    out, i = [], 0
    while len(buf) - i >= 13:
        if buf[i:i + 2] != b"TO":
            i += 1
            continue
        flags, module, ftype = buf[i + 2], buf[i + 3], buf[i + 4]
        hdr = 11 if flags & 2 else 9
        (n,) = struct.unpack_from("<I", buf, i + hdr - 4)
        if n > 4096:
            i += 1
            continue
        if len(buf) - i < hdr + n + 4:
            break
        (crc,) = struct.unpack_from("<I", buf, i + hdr + n)
        if zlib.crc32(buf[i:i + hdr + n]) & 0xFFFFFFFF != crc:
            i += 1
            continue
        out.append((module, ftype, bytes(buf[i + hdr:i + hdr + n])))
        i += hdr + n + 4
    return out, buf[i:]


class Session:
    def __init__(self, conn, args):
        self.conn, self.args = conn, args
        self.streaming = False
        self.lock = threading.Lock()
        self.offset = [0.0, 0.0]
        self.values = {d["key"]: SAVED.get(d["key"], d["default"]) for d in PARAM_DEFS}
        self.raw = (0.0, 0.0)

    def send(self, data):
        with self.lock:
            self.conn.sendall(data)

    def info(self):
        return {"product": "push_assist", "project": "push_assist", "firmware": "mock",
                "built": "Nov  2 2026 12:00:00", "partition": "ota_0", "pending_verify": False,
                "ip": "127.0.0.1", "left": True,
                "right": not self.args.no_right, "counts_per_N": COUNTS_PER_N, "full_scale_kg": 20,
                "rated_uV_per_V": 1000, "sps": self.args.sps,
                "pins": {"left_dat": 4, "left_clk": 5, "right_dat": 20, "right_clk": 21},
                "invert": {"left": False, "right": False}, "zero_tracking": True,
                "touch": {"left_gpio": 3, "right_gpio": 2, "left": True, "right": True,
                          "gate": bool(self.values["touch_gate"])}}

    def forces(self, t):
        push = 40 * max(0.0, math.sin(t * 0.6)) + 3
        turn = 12 * math.sin(t * 1.7)
        self.raw = (push + turn / 2, push - turn / 2)
        return self.raw[0] - self.offset[0], self.raw[1] - self.offset[1]

    def stream(self):
        t0 = time.time()
        while True:
            time.sleep(1 / self.args.sps)
            if not self.streaming:
                continue
            t = time.time() - t0
            left, right = self.forces(t)
            if self.args.no_right:
                right = float("nan")
            # a made-up zero drift on the left, followed by the tracker; the right sits still
            vals = [left, right, left + right, left - right, left * COUNTS_PER_N, right * COUNTS_PER_N,
                    -0.0007 * t, float("nan") if self.args.no_right else 0.0,
                    1.0 if abs(left) < 2 else 0.0, float("nan") if self.args.no_right else 0.0,
                    38.0 + t / 600]
            vals = self.touch(t, vals)
            rec = struct.pack("<I", int(t * 1e6) & 0xFFFFFFFF) + struct.pack("<%df" % len(vals), *vals)
            try:
                self.send(frame(TELEMETRY, 0x82, rec))
            except OSError:
                return

    def touch(self, t, vals):
        """Made-up pads: both handles held while the mock pushes (|force| > 2 N), the
        right handle keeping a 7 N offset after each push; the board's gate applied."""
        base = 6700.0
        out = vals[:2] + vals[2:]
        sent, extra = [], []
        for k in (0, 1):
            f = vals[k] + (7.0 if k == 1 and t > 5 else 0.0)
            held = abs(vals[k]) > 2
            raw = base + random.gauss(0, 1.5) + (780 if held else 0)
            pct = 100 * (raw - base) / base
            on = pct > self.values["touch_%s_on_pct" % "lr"[k]]
            if on and not getattr(self, "held%d" % k, False):
                setattr(self, "tare%d" % k, f - vals[k])
            setattr(self, "held%d" % k, on)
            tare = getattr(self, "tare%d" % k, 0.0)
            sent.append((f - tare if on else 0.0) if self.values["touch_gate"] else f)
            extra.append((f, pct, 1.0 if on else 0.0, tare, raw))
        out[0], out[1] = sent
        out[2], out[3] = sent[0] + sent[1], sent[0] - sent[1]
        return out + [extra[0][0], extra[1][0], extra[0][1], extra[1][1], extra[0][2], extra[1][2],
                      extra[0][3], extra[1][3], extra[0][4], extra[1][4]]

    def handle(self, module, ftype, payload):
        if module == TELEMETRY and ftype == 0x01:
            body = bytes([1, 0, len(CHANNELS)]) + b"".join(bytes([0, len(c)]) + c.encode() for c in CHANNELS)
            self.send(frame(TELEMETRY, 0x81, body))
        elif module == TELEMETRY and ftype == 0x02:
            self.streaming = bool(payload[0])
            self.send(frame(TELEMETRY, 0x83, bytes([ftype])))
        elif module == PUSH and ftype == 0x02:
            self.send(frame(PUSH, 0x82, json.dumps(self.info()).encode()))
        elif module == PUSH and ftype in (0x03, 0x06):  # GET_PARAMS, DEFAULT_PARAMS
            if ftype == 0x06:
                self.values = {d["key"]: d["default"] for d in PARAM_DEFS}
            self.send(frame(PUSH, ftype | 0x80, json.dumps({"params": self.params()}).encode()))
        elif module == PUSH and ftype == 0x04:  # SET_PARAM [key_len u8][key][value f32]
            if not payload or len(payload) != 1 + payload[0] + 4:
                return self.error(ftype, "SET_PARAM wants [key_len u8][key][value f32]")
            key = payload[1:1 + payload[0]].decode()
            (value,) = struct.unpack("<f", payload[1 + payload[0]:])
            d = next((d for d in PARAM_DEFS if d["key"] == key), None)
            if d is None:
                return self.error(ftype, "unknown key: " + key)
            if math.isnan(value) or math.isinf(value):
                return self.error(ftype, "value is not a finite number")
            self.values[key] = (1 if value else 0) if d.get("type") == "bool" else min(max(value, d["min"]), d["max"])
            self.send(frame(PUSH, 0x84, json.dumps(self.param(d)).encode()))
        elif module == PUSH and ftype == 0x05:  # SAVE_PARAMS
            SAVED.update(self.values)
            self.send(frame(PUSH, 0x85, bytes([1])))
        elif module == PUSH and ftype == 0x01:
            time.sleep(16 / self.args.sps)  # the firmware averages 16 readings
            self.offset = list(self.raw)
            self.send(frame(PUSH, 0x81, bytes([1, 0 if self.args.no_right else 1])))
        elif module == PUSH:
            self.error(ftype, "unknown request")

    def param(self, d):
        o = {k: v for k, v in d.items() if k != "type" or v == "bool"}
        o["value"] = self.values[d["key"]]
        return {k: o[k] for k in ("key", "label", "type", "unit", "value", "default", "min", "max", "step", "group") if k in o}

    def params(self):
        return [self.param(d) for d in PARAM_DEFS]

    def error(self, request, message):
        self.send(frame(PUSH, 0x8F, bytes([request]) + message.encode()))

    def run(self):
        threading.Thread(target=self.stream, daemon=True).start()
        buf = b""
        while True:
            d = self.conn.recv(4096)
            if not d:
                return
            frames, buf = parse(buf + d)
            for f in frames:
                self.handle(*f)


def discovery(args):
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    u.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    u.bind(("0.0.0.0", 5556))
    while True:
        d, addr = u.recvfrom(64)
        if d.startswith(b"PUSH?"):
            u.sendto(json.dumps({"product": "push_assist", "firmware": "mock"}).encode(), addr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sps", type=int, default=10)
    ap.add_argument("--no-right", action="store_true")
    args = ap.parse_args()
    threading.Thread(target=discovery, args=(args,), daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", 5555))
    srv.listen(1)
    print("mock board on tcp :5555, discovery on udp :5556", flush=True)
    while True:
        conn, addr = srv.accept()
        print("client", addr, flush=True)
        threading.Thread(target=Session(conn, args).run, daemon=True).start()


if __name__ == "__main__":
    main()
