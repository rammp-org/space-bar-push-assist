#!/usr/bin/env python3
"""Subscribe to the board's rammp::HandleForce over RTPS, as the MIB will, and
print what arrives. A check that the board publishes, without a MIB.

    python3 tools/rtps_listen.py                     # default interface
    python3 tools/rtps_listen.py --iface 192.168.4.2 # the laptop's address on the board's link
    python3 tools/rtps_listen.py --seconds 10        # stop after 10 s and print a summary

Needs Eclipse Cyclone DDS for Python (`pip install cyclonedds`; it has wheels for
Python 3.10-3.12, not 3.14). The type mirrors rammp-rtps
messages/push_assist_message.hpp field for field.
"""
import argparse
import math
import os
import sys
import time
from dataclasses import dataclass

TOPIC = "rammp/push_assist/handle_force"
TYPE = "rammp/msg/HandleForce"
FLAGS = {0: "left_ok", 1: "right_ok", 2: "left_zero_at_limit", 3: "right_zero_at_limit",
         4: "updating"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--iface", help="IPv4 address of the local interface on the board's network")
    ap.add_argument("--seconds", type=float, default=0, help="stop after this long (0 = until Ctrl-C)")
    a = ap.parse_args()
    if a.iface:
        os.environ["CYCLONEDDS_URI"] = (
            "<CycloneDDS><Domain><General><Interfaces>"
            f'<NetworkInterface address="{a.iface}"/>'
            "</Interfaces></General></Domain></CycloneDDS>")

    try:
        from cyclonedds.core import Policy, Qos
        from cyclonedds.domain import DomainParticipant
        from cyclonedds.idl import IdlStruct
        from cyclonedds.idl.types import float32, uint8, uint32
        from cyclonedds.sub import DataReader
        from cyclonedds.topic import Topic
    except ImportError:
        sys.exit("needs cyclonedds: pip install cyclonedds (Python 3.10-3.12)")

    @dataclass
    class HandleForce(IdlStruct, typename=TYPE):
        left_n: float32
        right_n: float32
        flags: uint8
        seq: uint32

    dp = DomainParticipant(0)
    topic = Topic(dp, TOPIC, HandleForce)
    # The board publishes best-effort; a reliable reader would not match it.
    reader = DataReader(dp, topic, qos=Qos(Policy.Reliability.BestEffort))

    print(f"listening for {TOPIC} ({TYPE})", flush=True)
    t0, n, first_seq, last_seq, last_print = time.time(), 0, None, None, 0.0
    try:
        while not a.seconds or time.time() - t0 < a.seconds:
            for s in reader.take(N=100):
                n += 1
                first_seq = s.seq if first_seq is None else first_seq
                last_seq = s.seq
                if time.time() - last_print >= 0.5:
                    last_print = time.time()
                    flags = ",".join(name for bit, name in FLAGS.items() if s.flags >> bit & 1)
                    fmt = lambda v: "  NaN " if math.isnan(v) else f"{v:+7.2f}"
                    print(f"seq {s.seq:7d}  left {fmt(s.left_n)} N  right {fmt(s.right_n)} N  "
                          f"[{flags or '-'}]", flush=True)
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    dt = time.time() - t0
    if n:
        lost = (last_seq - first_seq + 1) - n
        print(f"{n} samples in {dt:.1f} s ({n / dt:.1f}/s), seq {first_seq}..{last_seq}, "
              f"{lost} missing")
    else:
        print(f"no samples in {dt:.1f} s")


if __name__ == "__main__":
    main()
