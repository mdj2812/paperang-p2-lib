#!/usr/bin/env python3
"""Quick test for BtTransport — classic Bluetooth SPP connection to Paperang P2."""

import sys
import time

# Install from the branch first:
#   pip install git+https://github.com/mdj2812/paperang-p2-lib.git@feat/classic-bluetooth-spp

from paperang.transport import BtTransport

ADDRESS = sys.argv[1] if len(sys.argv) > 1 else None

# ── Device discovery ────────────────────────────────────────
print("1. Scanning for Paperang BT devices...")
devices = BtTransport.scan()
if devices:
    for addr, name in devices:
        print(f"   ✓ {addr}  {name}")
else:
    print("   ⚠ No devices found (need bluetoothctl installed)")

# ── Connect ──────────────────────────────────────────────────
if ADDRESS:
    addr = ADDRESS
elif devices:
    addr = devices[0][0]
else:
    print("ERROR: No address. Pass one: python3 test_bt.py 00:15:83:EB:05:17")
    sys.exit(1)

print(f"\n2. Connecting to {addr} ...")
transport = BtTransport(address=addr, timeout=10.0)
transport.connect()
print("   ✓ Connected!")

# ── Quick protocol test ─────────────────────────────────────
from paperang import PaperangP2

printer = PaperangP2(transport=transport)
print(f"   Battery: {printer.get_battery()}")
time.sleep(0.1)
print(f"   Version: {printer.get_version()}")
time.sleep(0.1)
print(f"   Status:  {printer.get_status()}")

transport.disconnect()
print("\n✓ All good — BtTransport works!")
