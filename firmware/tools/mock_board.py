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
import socket
import struct
import threading
import time
import zlib

CHANNELS = ["left_N", "right_N", "sum_N", "diff_N", "left_counts", "right_counts",
            "left_zero_N", "right_zero_N", "left_tracking", "right_tracking", "board_C"]
TELEMETRY, PUSH = 3, 0x30
COUNTS_PER_N = 10949.1  # 20 kg cell at 1.0 mV/V, as the firmware's nominal scale


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
        self.raw = (0.0, 0.0)

    def send(self, data):
        with self.lock:
            self.conn.sendall(data)

    def info(self):
        return {"product": "push_assist", "firmware": "mock", "ip": "127.0.0.1", "left": True,
                "right": not self.args.no_right, "counts_per_N": COUNTS_PER_N, "full_scale_kg": 20,
                "rated_uV_per_V": 1000, "sps": self.args.sps,
                "pins": {"left_dat": 20, "left_clk": 21, "right_dat": 4, "right_clk": 5},
                "invert": {"left": False, "right": False}, "zero_tracking": True}

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
            rec = struct.pack("<I", int(t * 1e6) & 0xFFFFFFFF) + struct.pack("<%df" % len(vals), *vals)
            try:
                self.send(frame(TELEMETRY, 0x82, rec))
            except OSError:
                return

    def handle(self, module, ftype, payload):
        if module == TELEMETRY and ftype == 0x01:
            body = bytes([1, 0, len(CHANNELS)]) + b"".join(bytes([0, len(c)]) + c.encode() for c in CHANNELS)
            self.send(frame(TELEMETRY, 0x81, body))
        elif module == TELEMETRY and ftype == 0x02:
            self.streaming = bool(payload[0])
            self.send(frame(TELEMETRY, 0x83, bytes([ftype])))
        elif module == PUSH and ftype == 0x02:
            self.send(frame(PUSH, 0x82, json.dumps(self.info()).encode()))
        elif module == PUSH and ftype == 0x01:
            time.sleep(16 / self.args.sps)  # the firmware averages 16 readings
            self.offset = list(self.raw)
            self.send(frame(PUSH, 0x81, bytes([1, 0 if self.args.no_right else 1])))

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
