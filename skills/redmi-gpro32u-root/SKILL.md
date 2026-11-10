---
name: redmi-gpro32u-root
description: Verify and troubleshoot runtime root on REDMI G Pro 32U 2026 (MiTV-MFFU1 / beekeeper, Android 14, OS3.0.120.0.UFFMAMN). Use when distinguishing ADB from root, checking DirtyFrag adaptation or recovery after reboot, or diagnosing why the 32U ADB switch and connection disagree. Do not assume other models or builds match.
---

# REDMI G Pro 32U root

1. Ask for the exact ADB selector or existing root-shell IP if it cannot be established locally. Never use the first attached Android device, guess an IP, or scan the network. Stay on a device the user owns or administers.
2. Run `scripts/probe.py adb --serial "$SERIAL"` for an already authorized ADB connection. Run `scripts/probe.py tcp --host "$MONITOR_IP"` only for an existing root channel explicitly identified by the user. Resolve the script relative to this skill. Both commands use Python 3 and send fixed read-only queries. The TCP transport is a shell, not ADB; port 5555 and port 2323 serve different purposes in the documented setup.
3. Report the selected transport, observed firmware, UID, SELinux, and bootloader state. An exact match with `uid=0` proves root over that transport. An exact match with a nonzero UID proves only that the tested channel is unprivileged. A timeout or open port alone proves neither. Stop before suggesting firmware-specific changes if any required device property differs.
4. For reboot recovery, use two confirmed root readings with different `boot_id` values. The second must be observed before manually launching the exploit. Sleep/wake or a changed UI switch is not enough. If the boot ID is unavailable, report that the comparison could not be made. Do not reboot unless asked.
5. Read [the Chinese tutorial](references/root-guide.zh-CN.md) for setup, ADB troubleshooting, and removal. Read [the adaptation notes](references/dirtyfrag-adaptation.zh-CN.md) only for the exact firmware and only when working on reproduction. They document the investigation; there is no bundled or independently verified build of a stock-to-root installer.

Keep checks read-only by default. Do not install or enable a passwordless network root listener, write vendor files or partitions, or run a root exploit as part of a check. Do not use the known-crashing `/proc/utopia_mdb/xc` node, even to collect diagnostics. Do not suggest flashing a 27U image or treat the Android robot screen as proof of Fastboot. Explain how to reverse changes before any requested state-changing experiment; get explicit confirmation before a data-wiping unlock. Remove local IPs, serial numbers, Bluetooth addresses, and boot IDs from public reports.
