#!/usr/bin/env python3
"""Flash the push-assist board over ethernet (espp OtaService, module 0), check
its image, confirm or reject it. Adapted from PACE RACER's tools/eth_link.py.

    python3 tools/ota_eth.py --ip 192.168.4.1 flash build-bench/push_assist.bin
    python3 tools/ota_eth.py --ip 192.168.4.1 flash build/push_assist.bin --no-confirm
    python3 tools/ota_eth.py --ip 192.168.4.1 status
    python3 tools/ota_eth.py --ip 192.168.4.1 mark-valid | rollback

`flash` sends the image, waits for the board to come back, then marks it valid.
With --no-confirm it leaves the new image pending: the board confirms itself
after a lease and 20 s of service, or a reset before that rolls it back.

Uses espp_ota from managed_components/espp__ota/python (there after a build).
"""
import argparse
import json
import os
import socket
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "managed_components", "espp__ota", "python"))
try:
    from espp_ota.client import OtaClient
except ImportError:
    sys.exit("espp_ota not found: build the firmware once (idf.py build) so managed_components/espp__ota exists")
from eth_bridge import SERVICE_PORT, _bind_for  # noqa: E402
from mock_board import frame, parse  # noqa: E402


class TcpTransport:
    """write(bytes, timeout_ms) / read(max_len, timeout_ms) -> bytes, b'' on
    timeout: what espp_ota.OtaClient expects of a transport."""

    def __init__(self, host, port=SERVICE_PORT):
        self.host, self.port, self.sock = host, port, None

    def __enter__(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _bind_for(s, self.host)
        s.settimeout(3.0)
        s.connect((self.host, self.port))
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock = s
        return self

    def __exit__(self, *exc):
        self.sock.close()

    def write(self, data, timeout_ms=5000):
        self.sock.settimeout(timeout_ms / 1000)
        self.sock.sendall(data)

    def read(self, max_len, timeout_ms=5000):
        self.sock.settimeout(timeout_ms / 1000)
        try:
            d = self.sock.recv(max_len)
        except socket.timeout:
            return b""
        if not d:
            raise ConnectionError("connection closed by the board")
        return d

    @property
    def description(self):
        return f"{self.host}:{self.port}"


def info(host):
    """push_assist GET_INFO (0x30/0x02) -> dict."""
    with socket.create_connection((host, SERVICE_PORT), timeout=3) as s:
        s.sendall(frame(0x30, 0x02, reply=False))
        buf, t0 = b"", time.time()
        while time.time() - t0 < 3:
            buf += s.recv(65536)
            frames, buf = parse(buf)
            for module, ftype, p in frames:
                if module == 0x30 and ftype == 0x82:
                    return json.loads(p)
    raise TimeoutError("no INFO reply")


def wait_for_board(host, timeout=90.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            return info(host)
        except (OSError, ValueError, TimeoutError):
            time.sleep(1.0)
    raise TimeoutError(f"{host}: no answer on :{SERVICE_PORT} after {timeout:.0f} s")


def flash(host, binary, confirm=True):
    image = open(binary, "rb").read()
    before = info(host)
    print(f"flashing {os.path.basename(binary)} ({len(image) / 1024:.0f} KiB) -> {host}; running "
          f"{before.get('firmware')} on {before.get('partition')}", flush=True)
    last = [0]

    def prog(written, total):
        pct = int(100 * written / max(total, 1))
        if pct // 10 != last[0] // 10:
            print(f"  {pct}%", flush=True)
        last[0] = pct

    t0 = time.time()
    with TcpTransport(host) as t:
        OtaClient(t, chunk_size=4096, progress=prog).flash(image, image_size=len(image))
    print(f"sent in {time.time() - t0:.1f} s; board restarting", flush=True)
    time.sleep(3.0)
    after = wait_for_board(host)
    print(f"back: {after.get('firmware')} built {after.get('built')} on {after.get('partition')}, "
          f"pending_verify={after.get('pending_verify')}", flush=True)
    if confirm and after.get("pending_verify"):
        with TcpTransport(host) as t:
            OtaClient(t).mark_valid()
        print("marked valid: rollback cancelled", flush=True)
    return after


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ip", default="192.168.4.1")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("flash")
    f.add_argument("binary")
    f.add_argument("--no-confirm", action="store_true", help="leave the new image pending verify")
    sub.add_parser("status")
    sub.add_parser("mark-valid")
    sub.add_parser("rollback")
    a = ap.parse_args()
    if a.cmd == "flash":
        flash(a.ip, a.binary, confirm=not a.no_confirm)
    elif a.cmd == "status":
        i = info(a.ip)
        print(json.dumps({k: i.get(k) for k in ("project", "firmware", "built", "partition", "pending_verify")}))
    elif a.cmd == "mark-valid":
        with TcpTransport(a.ip) as t:
            OtaClient(t).mark_valid()
        print("marked valid")
    elif a.cmd == "rollback":
        with TcpTransport(a.ip) as t:
            OtaClient(t).mark_invalid()
        print("marked invalid: the board rolls back and reboots")


if __name__ == "__main__":
    main()
