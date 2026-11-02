#!/usr/bin/env python3
"""Serve the push-assist dashboard and bridge its WebSocket to the board's
ethernet service stream (tcp :5555). Browsers cannot open raw TCP sockets, so
this relays the bytes; the page does all the protocol work.

    python3 tools/eth_bridge.py              # http://localhost:8765/
    python3 tools/eth_bridge.py --port 9000
    python3 tools/eth_bridge.py --list       # ask the LAN who is there and exit

Endpoints:
    GET  /                     web/dashboard.html
    GET  /<file>               other files under web/ (the alex-style assets)
    GET  /discover             JSON list of boards answering "PUSH?" on udp :5556
    WS   /ws?target=<ip>       raw bytes <-> tcp <ip>:5555, one socket per page session

Standard library only. Adapted from PACE RACER's atos-drive tools
(eth_bridge.py and eth_link.py's interface and discovery helpers).
"""
import argparse
import base64
import hashlib
import json
import mimetypes
import os
import socket
import struct
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.realpath(os.path.join(HERE, "..", "web"))
SERVICE_PORT = 5555
DISCOVERY_PORT = 5556
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
IP_BOUND_IF = 25  # macOS setsockopt(IPPROTO_IP, ...) to pin a socket to one interface

# ---------------------------------------------------------------- interfaces
_SKIP_IFACES = ("utun", "lo", "bridge", "awdl", "llw", "docker", "veth", "virbr", "tailscale",
                "Loopback", "vEthernet", "Tailscale")


def _prefix_to_mask(bits):
    return socket.inet_ntoa(((0xFFFFFFFF << (32 - bits)) & 0xFFFFFFFF).to_bytes(4, "big"))


def _ifaces_macos():
    out = subprocess.run(["ifconfig"], capture_output=True, text=True).stdout
    found, name = [], None
    for ln in out.splitlines():
        if ln and not ln[0].isspace():
            name = ln.split(":")[0]
        elif name and "inet " in ln:
            parts = ln.split()
            mask = "255.255.255.255"
            if "netmask" in parts:
                mask = socket.inet_ntoa(int(parts[parts.index("netmask") + 1], 16).to_bytes(4, "big"))
            found.append((name, parts[1], mask))
    return found


def _ifaces_linux():
    out = subprocess.run(["ip", "-4", "-o", "addr", "show"], capture_output=True, text=True).stdout
    found = []
    for ln in out.splitlines():
        parts = ln.split()
        if "inet" in parts:
            ip, bits = parts[parts.index("inet") + 1].split("/")
            found.append((parts[1], ip, _prefix_to_mask(int(bits))))
    return found


def _ifaces_windows():
    ps = ("Get-NetIPAddress -AddressFamily IPv4 | "
          "Select-Object InterfaceAlias,IPAddress,PrefixLength | ConvertTo-Json -Compress")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True).stdout.strip()
    rows = json.loads(out) if out else []
    if isinstance(rows, dict):  # one address: PowerShell returns an object, not a list
        rows = [rows]
    return [(r["InterfaceAlias"], r["IPAddress"], _prefix_to_mask(int(r["PrefixLength"]))) for r in rows]


def _ifaces():
    """[(name, ipv4, netmask)] of physical interfaces with an IPv4 address.
    Empty if the OS tool is missing or its output is not understood: callers
    then fall back to the OS's own routing."""
    try:
        if sys.platform == "darwin":
            found = _ifaces_macos()
        elif sys.platform.startswith("win"):
            found = _ifaces_windows()
        else:
            found = _ifaces_linux()
    except (OSError, ValueError, KeyError, IndexError):
        return []
    return [(n, ip, m) for n, ip, m in found
            if not n.startswith(_SKIP_IFACES) and not ip.startswith("127.")]


def _pin_to_iface(sock, name):
    """Best-effort: keep the socket's traffic on one interface, so a VPN that
    claims the same range (Tailscale's utun takes 169.254/16 on macOS) cannot
    swallow it."""
    try:
        if sys.platform == "darwin":
            sock.setsockopt(socket.IPPROTO_IP, IP_BOUND_IF, socket.if_nametoindex(name))
        elif sys.platform.startswith("linux") and hasattr(socket, "SO_BINDTODEVICE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, name.encode())
    except OSError:
        pass


def _same_subnet(ip, net_ip, mask):
    a, b, m = (int.from_bytes(socket.inet_aton(x), "big") for x in (ip, net_ip, mask))
    return (a & m) == (b & m)


def _bind_for(sock, target_ip):
    """Bind the socket's source to the interface that owns the target's subnet."""
    for name, ip, mask in _ifaces():
        if _same_subnet(target_ip, ip, mask):
            sock.bind((ip, 0))
            _pin_to_iface(sock, name)
            return name
    return None


# ---------------------------------------------------------------- discovery
def discover(timeout=1.5):
    """Broadcast "PUSH?" from every physical interface; return [info dict] with 'ip'."""
    socks = []
    for name, ip, mask in (_ifaces() or [(None, "0.0.0.0", "0.0.0.0")]):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((ip, 0))
        except OSError:
            s.close()
            continue
        if name:
            _pin_to_iface(s, name)
        s.setblocking(False)
        socks.append(s)
        dsts = {"255.255.255.255"}
        if name:
            ipn = int.from_bytes(socket.inet_aton(ip), "big")
            mn = int.from_bytes(socket.inet_aton(mask), "big")
            dsts.add(socket.inet_ntoa(((ipn & mn) | (~mn & 0xFFFFFFFF)).to_bytes(4, "big")))
        for dst in dsts:
            try:
                s.sendto(b"PUSH?", (dst, DISCOVERY_PORT))
            except OSError:
                pass
    boards, t0 = {}, time.time()
    while time.time() - t0 < timeout:
        for s in socks:
            try:
                data, (ip, _) = s.recvfrom(2048)
            except OSError:  # BlockingIOError, and Windows' WSAECONNRESET after an ICMP unreachable
                continue
            try:
                info = json.loads(data.decode())
            except ValueError:
                continue
            info["ip"] = ip
            boards[ip] = info
        time.sleep(0.05)
    for s in socks:
        s.close()
    return sorted(boards.values(), key=lambda b: b["ip"])


# ---------------------------------------------------------------- websocket
def ws_frame(opcode, payload=b""):
    hdr = bytes([0x80 | opcode])
    n = len(payload)
    if n < 126:
        hdr += bytes([n])
    elif n < 65536:
        hdr += bytes([126]) + struct.pack(">H", n)
    else:
        hdr += bytes([127]) + struct.pack(">Q", n)
    return hdr + payload


def ws_read(rfile):
    """-> (opcode, payload) or None on EOF. Client frames are always masked."""
    h = rfile.read(2)
    if len(h) < 2:
        return None
    fin_op, ln = h[0], h[1]
    opcode, masked, n = fin_op & 0x0F, ln & 0x80, ln & 0x7F
    if n == 126:
        n = struct.unpack(">H", rfile.read(2))[0]
    elif n == 127:
        n = struct.unpack(">Q", rfile.read(8))[0]
    mask = rfile.read(4) if masked else b""
    data = rfile.read(n)
    if masked:
        data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    return opcode, data


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/ws":
            return self.websocket(parse_qs(u.query).get("target", [""])[0])
        if u.path == "/discover":
            return self.reply(200, "application/json", json.dumps(discover()).encode())
        rel = "dashboard.html" if u.path in ("/", "") else u.path.lstrip("/")
        path = os.path.realpath(os.path.join(WEB, rel))
        if not path.startswith(WEB + os.sep) or not os.path.isfile(path):  # no path tricks
            return self.send_error(404)
        with open(path, "rb") as fh:
            ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
            return self.reply(200, ctype, fh.read())

    def reply(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def websocket(self, target):
        key = self.headers.get("Sec-WebSocket-Key")
        if self.headers.get("Upgrade", "").lower() != "websocket" or not key or not target:
            self.send_error(400, "websocket upgrade with ?target=<ip> expected")
            return
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _bind_for(tcp, target)
        tcp.settimeout(3.0)
        try:
            tcp.connect((target, SERVICE_PORT))
        except OSError as e:
            self.send_error(502, f"connect {target}:{SERVICE_PORT}: {e}")
            return
        tcp.settimeout(None)
        tcp.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self.close_connection = True
        wlock = threading.Lock()

        # ValueError: the handler already returned and closed wfile (page went away).
        def board_to_ws():
            try:
                while True:
                    d = tcp.recv(65536)
                    if not d:
                        break
                    with wlock:
                        self.wfile.write(ws_frame(0x2, d))
                        self.wfile.flush()
            except (OSError, ValueError):
                pass
            finally:
                with wlock:
                    try:
                        self.wfile.write(ws_frame(0x8, struct.pack(">H", 1001)))
                        self.wfile.flush()
                    except (OSError, ValueError):
                        pass

        t = threading.Thread(target=board_to_ws, daemon=True)
        t.start()
        try:
            while True:
                fr = ws_read(self.rfile)
                if fr is None:
                    break
                op, data = fr
                if op in (0x1, 0x2):
                    tcp.sendall(data)
                elif op == 0x9:
                    with wlock:
                        self.wfile.write(ws_frame(0xA, data))
                        self.wfile.flush()
                elif op == 0x8:
                    break
        except OSError:
            pass
        finally:
            try:
                tcp.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            tcp.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--list", action="store_true", help="print the boards that answer and exit")
    a = ap.parse_args()
    if a.list:
        boards = discover()
        for b in boards:
            print(json.dumps(b))
        if not boards:
            print("no boards answered PUSH? on udp :%d" % DISCOVERY_PORT, file=sys.stderr)
        return
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"dashboard: http://localhost:{a.port}/   (Ctrl-C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
