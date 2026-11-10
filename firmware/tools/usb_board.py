#!/usr/bin/env python3
"""The board over its USB-C console, for the dashboard without ethernet.

Reads the CSV rows the firmware prints on UART0 (PA_CONSOLE_CSV) and serves them on
tcp :5555 / udp :5556 with the same protocol as the board, so the dashboard shows the live
handle forces and the MIB linear / angular they map to. Read-only: tare is done here, on
the host (the board's own tare and zero tracking keep running underneath). Params go to
the board as console commands (`pa params`, `pa set <key> <value>`, `pa save`,
`pa defaults`, answered with one `PA <kind> <json>` line), so the touch threshold and the
other settings work over USB too.

    python3 tools/usb_board.py                      # finds /dev/cu.usbmodem* / ttyUSB* / ttyACM*
    python3 tools/usb_board.py --port /dev/cu.usbmodem5C930891181 --csv run.csv
    python3 tools/eth_bridge.py                     # then open http://localhost:8765/, connect to 127.0.0.1

Standard library only (termios: macOS and Linux).
"""
import argparse
import glob
import json
import os
import queue
import re
import select
import socket
import struct
import termios
import threading
import time

import mock_board as mb

HEADER = "time_s,left_N,right_N"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
OLD_COLUMNS = ["time_s"] + mb.CHANNELS[:11]  # firmware before the touch probe


class Console:
    """Latest CSV row from the board's console, plus a condition for new rows."""

    def __init__(self, port, baud, csv_path):
        self.port, self.baud = port, baud
        self.cv = threading.Condition()
        self.row, self.seq, self.rows = None, 0, 0
        self.cols, self.fd, self.wlock, self.replies = OLD_COLUMNS, None, threading.Lock(), queue.Queue()
        self.touch_gpio = [0, 0]
        self.csv = open(csv_path, "a") if csv_path else None
        threading.Thread(target=self.run, daemon=True).start()

    def open(self):
        fd = os.open(self.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        a = termios.tcgetattr(fd)
        speed = getattr(termios, "B%d" % self.baud)
        a[0] = 0                                             # iflag: raw
        a[1] = 0                                             # oflag
        a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL  # cflag
        a[3] = 0                                             # lflag: no echo, no canonical
        a[4] = a[5] = speed
        termios.tcsetattr(fd, termios.TCSANOW, a)
        return fd

    def run(self):
        while True:
            try:
                fd = self.open()
            except OSError as e:
                print("waiting for %s (%s)" % (self.port, e), flush=True)
                time.sleep(1)
                continue
            self.fd = fd
            print("reading %s at %d baud" % (self.port, self.baud), flush=True)
            buf = b""
            try:
                while True:
                    r, _, _ = select.select([fd], [], [], 1.0)
                    if not r:
                        continue
                    d = os.read(fd, 4096)
                    if not d:
                        raise OSError("port closed")
                    buf += d
                    *lines, buf = buf.split(b"\n")
                    for ln in lines:
                        self.line(ln.decode(errors="replace").strip())
            except OSError as e:
                print("lost %s (%s), retrying" % (self.port, e), flush=True)
                os.close(fd)
                time.sleep(1)

    def command(self, cmd, timeout=3.0):
        """Send one console command; -> (kind, json body), or ("error", message)."""
        while not self.replies.empty():
            self.replies.get_nowait()
        if self.fd is None:
            return "error", {"message": "the board's console is not open"}
        with self.wlock:
            os.write(self.fd, (cmd + "\n").encode())
        try:
            kind, body = self.replies.get(timeout=timeout)
        except queue.Empty:
            return "error", {"message": "no answer to '%s': flash the firmware with console commands" % cmd}
        try:
            return kind, json.loads(body)
        except ValueError:
            return kind, body

    def line(self, s):
        s = ANSI.sub("", s)  # a log line's colour reset can lead the next line
        m = re.search(r"Touch pad (\d) on GPIO (\d+)", s)
        if m:
            self.touch_gpio[int(m.group(1))] = int(m.group(2))
        if s.startswith("PA "):
            kind, _, body = s[3:].partition(" ")
            self.replies.put((kind, body))
            return
        if s.startswith(HEADER):
            self.cols = s.split(",")
            if self.csv and self.rows == 0:
                self.csv.write(s + "\n")
            return
        parts = s.split(",")
        if len(parts) != len(self.cols):
            if s and not s[0].isdigit():
                print("board:", s, flush=True)               # boot log, warnings
            return
        try:
            vals = [float(p) for p in parts]
        except ValueError:
            return
        if self.csv:
            self.csv.write(s + "\n")
            self.csv.flush()
        named = dict(zip(self.cols, vals))
        vals = [named.get("time_s", 0.0)] + [named.get(c, float("nan")) for c in mb.CHANNELS]
        with self.cv:
            self.row, self.seq = vals, self.seq + 1
            self.rows += 1
            self.cv.notify_all()


class Session(mb.Session):
    """mock_board's protocol, fed by the console instead of made-up forces."""

    def __init__(self, conn, args, console):
        super().__init__(conn, args)
        self.console = console
        self.offset = [0.0, 0.0]

    def info(self):
        i = super().info()
        row = self.console.row
        pad = lambda side: bool(row) and row[1 + mb.CHANNELS.index(side + "_touch_raw")] == row[1 + mb.CHANNELS.index(side + "_touch_raw")]
        i.update(firmware="usb console", ip="usb:" + self.console.port,
                 left=bool(row) and row[1] == row[1], right=bool(row) and row[2] == row[2],
                 touch={"left_gpio": self.console.touch_gpio[0], "right_gpio": self.console.touch_gpio[1],
                        "left": pad("left"), "right": pad("right"), "gate": None})
        return i

    def stream(self):
        seen = 0
        while True:
            with self.console.cv:
                self.console.cv.wait_for(lambda: self.console.seq != seen, timeout=2.0)
                row, seen = self.console.row, self.console.seq
            if row is None or not self.streaming:
                continue
            t, vals = row[0], list(row[1:])
            self.raw = (vals[0], vals[1])
            vals[0] -= self.offset[0]
            vals[1] -= self.offset[1]
            vals[2], vals[3] = vals[0] + vals[1], vals[0] - vals[1]
            rec = struct.pack("<I", int(t * 1e6) & 0xFFFFFFFF) + struct.pack("<%df" % len(vals), *vals)
            try:
                self.send(mb.frame(mb.TELEMETRY, 0x82, rec))
            except OSError:
                return

    def reply(self, ftype, kind, body, want):
        if kind != want:
            return self.error(ftype, body.get("message", str(body)) if isinstance(body, dict) else str(body))
        payload = bytes([int(body)]) if want == "saved" else json.dumps(body).encode()
        self.send(mb.frame(mb.PUSH, ftype | 0x80, payload))

    def handle(self, module, ftype, payload):
        if module == mb.PUSH and ftype == 0x01:              # TARE: the board's, else on the host
            kind, body = self.console.command("pa tare", timeout=5.0)
            if kind == "tared":
                self.offset = [0.0, 0.0]
                return self.send(mb.frame(mb.PUSH, 0x81, bytes(int(x) for x in body)))
            time.sleep(1.5)
            self.offset = list(self.raw)
            self.send(mb.frame(mb.PUSH, 0x81, bytes([1, 1])))
        elif module == mb.PUSH and ftype == 0x04:                # SET_PARAM [key_len u8][key][value f32]
            if not payload or len(payload) != 1 + payload[0] + 4:
                return self.error(ftype, "SET_PARAM wants [key_len u8][key][value f32]")
            key = payload[1:1 + payload[0]].decode()
            (value,) = struct.unpack("<f", payload[1 + payload[0]:])
            self.reply(ftype, *self.console.command("pa set %s %r" % (key, value)), want="param")
        elif module == mb.PUSH and ftype in (0x03, 0x05, 0x06):  # GET_PARAMS, SAVE_PARAMS, DEFAULT_PARAMS
            cmd, want = {0x03: ("pa params", "params"), 0x05: ("pa save", "saved"), 0x06: ("pa defaults", "defaults")}[ftype]
            self.reply(ftype, *self.console.command(cmd), want=want)
        else:
            super().handle(module, ftype, payload)


def find_port():
    for pat in ("/dev/cu.usbmodem*", "/dev/cu.wchusbserial*", "/dev/cu.usbserial*", "/dev/ttyACM*", "/dev/ttyUSB*"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[0]
    raise SystemExit("no USB serial port found; pass --port")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serial device (default: first USB serial port)")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--csv", help="also append every row to this CSV")
    args = ap.parse_args()
    args.sps, args.no_right = 11, False
    console = Console(args.port or find_port(), args.baud, args.csv)
    threading.Thread(target=mb.discovery, args=(args,), daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 5555))
    srv.listen(1)
    print("USB board on tcp 127.0.0.1:5555; run tools/eth_bridge.py and connect to 127.0.0.1", flush=True)
    while True:
        conn, addr = srv.accept()
        print("dashboard connected", flush=True)
        threading.Thread(target=Session(conn, args, console).run, daemon=True).start()


if __name__ == "__main__":
    main()
