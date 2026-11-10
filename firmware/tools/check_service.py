#!/usr/bin/env python3
"""Exercise the board's push_assist module (0x30) over the service stream:
GET_INFO, GET_PARAMS, SET_PARAM (clamping, a bad key), and with --save the
SAVE_PARAMS / DEFAULT_PARAMS round trip. Prints PASS or FAIL per check.

    python3 tools/check_service.py --ip 192.168.4.1          # the board
    python3 tools/check_service.py --ip 127.0.0.1            # tools/mock_board.py
    python3 tools/check_service.py --ip 192.168.4.1 --save   # also writes NVS (restored after)

Leaves every param as it found it. Standard library only.
"""
import argparse
import json
import os
import socket
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mock_board import frame, parse  # noqa: E402

PUSH = 0x30


class Link:
    def __init__(self, ip):
        self.s = socket.create_connection((ip, 5555), timeout=3)
        self.buf = b""

    def ask(self, ftype, payload=b"", want=None, timeout=4.0):
        """Send a request; return (type, payload) of the next push_assist reply."""
        self.s.sendall(frame(PUSH, ftype, payload, reply=False))
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                self.buf += self.s.recv(65536)
            except socket.timeout:
                continue
            frames, self.buf = parse(self.buf)
            for module, rtype, p in frames:
                if module == PUSH and (want is None or rtype in want):
                    return rtype, p
        raise TimeoutError(f"no reply to 0x{ftype:02x}")


def set_param(link, key, value):
    k = key.encode()
    return link.ask(0x04, bytes([len(k)]) + k + struct.pack("<f", value), want={0x84, 0x8F})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ip", default="192.168.4.1")
    ap.add_argument("--save", action="store_true", help="also test SAVE_PARAMS and DEFAULT_PARAMS")
    a = ap.parse_args()
    link, fails = Link(a.ip), 0

    def check(name, ok, detail=""):
        nonlocal fails
        fails += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail else ''}", flush=True)

    t, p = link.ask(0x02, want={0x82})
    info = json.loads(p)
    check("GET_INFO has the image fields", all(k in info for k in ("project", "built", "partition", "pending_verify")),
          f"project={info.get('project')} partition={info.get('partition')} pending_verify={info.get('pending_verify')}")
    check("project is push_assist", info.get("project") == "push_assist")

    t, p = link.ask(0x03, want={0x83})
    params = {q["key"]: q for q in json.loads(p)["params"]}
    check("GET_PARAMS lists the params", len(params) >= 10, ", ".join(params))
    before = {k: q["value"] for k, q in params.items()}

    t, p = set_param(link, "zt_band_n", 99)
    q = json.loads(p) if t == 0x84 else {}
    check("SET_PARAM clamps to max", t == 0x84 and q.get("value") == q.get("max"), f"-> {q.get('value')}")
    t, p = set_param(link, "zt_band_n", 1.5)
    check("SET_PARAM sets a value", t == 0x84 and abs(json.loads(p)["value"] - 1.5) < 1e-6)
    t, p = set_param(link, "no_such_key", 1)
    check("SET_PARAM unknown key -> 0x8F", t == 0x8F and p[0] == 0x04, p[1:].decode(errors="replace"))
    t, p = link.ask(0x09, want={0x8F})
    check("unknown request -> 0x8F", t == 0x8F and p[0] == 0x09)

    if a.save:
        t, p = link.ask(0x05, want={0x85})
        check("SAVE_PARAMS", t == 0x85 and p == b"\x01")
        t, p = link.ask(0x06, want={0x86})
        q = {x["key"]: x for x in json.loads(p)["params"]}
        check("DEFAULT_PARAMS returns defaults", all(x["value"] == x["default"] for x in q.values()))

    for k, v in before.items():  # put everything back as it was
        set_param(link, k, v)
    if a.save:
        link.ask(0x05, want={0x85})
    t, p = link.ask(0x03, want={0x83})
    after = {q["key"]: q["value"] for q in json.loads(p)["params"]}
    check("params restored", all(abs(after[k] - v) < 1e-6 for k, v in before.items()))
    print("all passed" if not fails else f"{fails} failed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
