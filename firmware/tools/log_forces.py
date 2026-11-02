#!/usr/bin/env python3
"""Log the board's telemetry to CSV, for long unattended runs (zero drift,
creep, warm-up). Prints one summary line a minute: each channel's mean over
that minute and its change since the first minute.

    python3 tools/log_forces.py                         # find the board, log until Ctrl-C
    python3 tools/log_forces.py --ip 192.168.4.1 --minutes 60 --out drift.csv

The board serves one client at a time: this takes over from an open dashboard.
Standard library only.
"""
import argparse
import os
import socket
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eth_bridge import SERVICE_PORT, _bind_for, discover  # noqa: E402
from mock_board import frame, parse  # noqa: E402

TELEMETRY = 3


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ip", help="board IP (default: discover)")
    ap.add_argument("--minutes", type=float, default=0, help="stop after this long (0 = until Ctrl-C)")
    ap.add_argument("--out", default=time.strftime("drift_%Y%m%d_%H%M%S.csv"))
    a = ap.parse_args()

    ip = a.ip
    if not ip:
        boards = discover()
        if len(boards) != 1:
            sys.exit(f"found {len(boards)} boards; pass --ip")
        ip = boards[0]["ip"]
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _bind_for(s, ip)
    s.settimeout(3)
    s.connect((ip, SERVICE_PORT))
    s.sendall(frame(TELEMETRY, 0x01, reply=False))                       # GET_SCHEMA
    s.sendall(frame(TELEMETRY, 0x02, bytes([1, 100, 0]), reply=False))  # SET_STREAM on

    channels, buf, t_start = None, b"", time.time()
    minute, first, n_rows, mins = [], None, 0, 0
    next_summary = t_start + 60
    print(f"logging {ip} to {a.out}", flush=True)
    with open(a.out, "w") as out:
        try:
            while not a.minutes or time.time() - t_start < a.minutes * 60:
                try:
                    d = s.recv(65536)
                except socket.timeout:
                    continue
                if not d:
                    sys.exit("board closed the connection")
                frames, buf = parse(buf + d)
                for module, ftype, p in frames:
                    if module != TELEMETRY:
                        continue
                    if ftype == 0x81:  # SCHEMA
                        n, o, channels = p[2], 3, []
                        for _ in range(n):
                            ln = p[o + 1]
                            channels.append(p[o + 2:o + 2 + ln].decode())
                            o += 2 + ln
                        out.write("host_s,device_s," + ",".join(channels) + "\n")
                    elif ftype == 0x82 and channels:  # SAMPLE records
                        rec = 4 + 4 * len(channels)
                        for o in range(0, len(p) - rec + 1, rec):
                            us = struct.unpack_from("<I", p, o)[0]
                            vals = struct.unpack_from("<%df" % len(channels), p, o + 4)
                            host = time.time() - t_start
                            out.write(f"{host:.3f},{us / 1e6:.3f}," + ",".join(f"{v:.4f}" for v in vals) + "\n")
                            minute.append(vals)
                            n_rows += 1
                if minute and time.time() >= next_summary:
                    means = [sum(v[k] for v in minute) / len(minute) for k in range(len(channels))]
                    first = first or means
                    mins += 1
                    print(f"{mins:4d} min  " + "  ".join(
                        f"{c} {m:+.3f} ({m - f:+.3f})" for c, m, f in zip(channels, means, first)
                        if c.endswith("_N")), flush=True)
                    out.flush()
                    minute, next_summary = [], next_summary + 60
        except KeyboardInterrupt:
            pass
    print(f"{n_rows} samples in {a.out}")


if __name__ == "__main__":
    main()
