#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only identification and root check for one explicitly selected 32U."""

import argparse
import ipaddress
import json
import re
import secrets
import socket
import subprocess
import time


PROFILE = {
    "model": "MiTV-MFFU1",
    "device": "beekeeper",
    "android": "14",
    "firmware": "OS3.0.120.0.UFFMAMN",
    "kernel": "5.15.148-android14-11-g37010446f523",
}

# This table is deliberately fixed: neither transport accepts remote commands.
READS = {
    "model": "getprop ro.product.model",
    "device": "getprop ro.product.device",
    "android": "getprop ro.build.version.release",
    "firmware": "getprop ro.build.version.incremental",
    "kernel": "uname -r",
    "security_patch": "getprop ro.build.version.security_patch",
    "verified_boot": "getprop ro.boot.verifiedbootstate",
    "bootloader": "getprop ro.boot.vbmeta.device_state",
    "boot_completed": "getprop sys.boot_completed",
    "boot_id": "cat /proc/sys/kernel/random/boot_id",
    "uid": "id -u",
    "selinux": "getenforce",
    "context": "cat /proc/self/attr/current",
    "adbd": "getprop init.svc.adbd",
    "adb_tcp_port": "getprop service.adb.tcp.port",
}
MAX_REPLY = 16384


class ProbeError(Exception):
    pass


def probe_command(token):
    lines = [f"printf '%s\\n' '{token}begin'"]
    lines.extend(
        f"printf '%s%s\\n' '{token}{key}=' \"$({command} 2>/dev/null)\""
        for key, command in READS.items()
    )
    lines.append(f"printf '%s\\n' '{token}end'")
    return "\n".join(lines)


def parse_reply(raw, token):
    if len(raw) > MAX_REPLY:
        raise ProbeError("reply exceeds the expected size")
    fields = {}
    started = False
    for line in raw.decode("utf-8", "replace").splitlines():
        if line == token + "begin":
            if started:
                raise ProbeError("duplicate probe frame")
            started = True
            continue
        if not started or not line.startswith(token):
            continue
        if line == token + "end":
            if set(READS) != set(fields):
                raise ProbeError("incomplete device response")
            return fields
        key, sep, value = line[len(token) :].partition("=")
        if not sep or key not in READS or key in fields:
            raise ProbeError("unexpected probe field")
        fields[key] = value.strip()
    raise ProbeError("device did not complete the read-only probe")


def summarize(fields, transport):
    uid = fields["uid"]
    if not uid.isascii() or not uid.isdecimal() or len(uid) > 10:
        raise ProbeError("device did not return a numeric UID")
    report = {key: value or None for key, value in fields.items()}
    report["uid"] = int(uid)
    report["transport"] = transport
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", fields["boot_id"]):
        report["boot_id"] = None
    report["mismatched_fields"] = [key for key, value in PROFILE.items() if fields[key] != value]
    if report["mismatched_fields"]:
        report["status"] = "target_mismatch"
        return report, 2
    report["status"] = "root_verified" if report["uid"] == 0 else "non_root_shell"
    return report, 0 if report["uid"] == 0 else 1


def adb_read(args, command):
    completed = subprocess.run(
        [args.adb, "-s", args.serial, "shell", command],
        capture_output=True, stdin=subprocess.DEVNULL, timeout=args.timeout, check=False,
    )
    if completed.returncode:
        status = (completed.stdout + completed.stderr).lower()
        for keyword in (b"unauthorized", b"offline", b"not found"):
            if keyword in status:
                raise ProbeError("ADB target " + keyword.decode("ascii"))
        raise ProbeError("ADB shell failed; check the selected transport")
    return completed.stdout


def tcp_read(args, command, token):
    deadline = time.monotonic() + args.timeout
    marker = (token + "end\n").encode("ascii")
    crlf_marker = (token + "end\r\n").encode("ascii")
    received = bytearray()
    with socket.create_connection((str(args.host), args.port), timeout=args.timeout) as conn:
        conn.settimeout(max(0.01, deadline - time.monotonic()))
        conn.sendall((command + "\nexit\n").encode("ascii"))
        while marker not in received and crlf_marker not in received:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProbeError("root channel timed out")
            conn.settimeout(remaining)
            data = conn.recv(4096)
            if not data:
                break
            received.extend(data)
            if len(received) > MAX_REPLY:
                raise ProbeError("reply exceeds the expected size")
    return bytes(received)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="transport", required=True)
    adb = sub.add_parser("adb", help="inspect one already-connected ADB device")
    adb.add_argument("--serial", required=True, help="exact selector from adb devices")
    adb.add_argument("--adb", default="adb", help="path to the adb executable")
    tcp = sub.add_parser("tcp", help="verify an existing root shell, not just an open port")
    tcp.add_argument("--host", type=ipaddress.ip_address, required=True, help="explicit IP address")
    tcp.add_argument("--port", type=int, default=2323)
    for cmd in (adb, tcp):
        cmd.add_argument("--timeout", type=float, default=8, help="seconds, 1 to 30")
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 30:
        parser.error("--timeout must be between 1 and 30 seconds")
    if args.transport == "tcp" and not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    token = "GPRO32_" + secrets.token_hex(6) + "_"
    command = probe_command(token)
    try:
        raw = adb_read(args, command) if args.transport == "adb" else tcp_read(args, command, token)
        report, code = summarize(parse_reply(raw, token), args.transport)
    except (TimeoutError, subprocess.TimeoutExpired):
        report, code = {"status": "probe_failed", "reason": "connection or shell timed out"}, 2
    except OSError as error:
        report, code = {"status": "probe_failed", "reason": type(error).__name__}, 2
    except ProbeError as error:
        report, code = {"status": "probe_failed", "reason": str(error)}, 2
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
