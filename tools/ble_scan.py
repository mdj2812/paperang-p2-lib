"""Scan BLE devices to find Paperang P2 MAC and service UUIDs."""
import asyncio
import sys

try:
    from bleak import BleakScanner, BleakClient
except ImportError:
    print("bleak not installed. Run: pip install bleak")
    sys.exit(1)

TARGET_PREFIX = ""  # Paperang MAC prefix if known


async def scan():
    print("Scanning for BLE devices (10s)...")
    devices = await BleakScanner.discover(timeout=10)
    if not devices:
        print("No devices found.")
        return

    print(f"\nFound {len(devices)} device(s):")
    for d in devices:
        marker = ""
        if d.name and "paperang" in d.name.lower():
            marker = " ★ PAPERANG?"
        print(f"  {d.address}  RSSI={d.rssi:>4}  {d.name or '(no name)'}{marker}")

    # Try to discover services for each device
    print("\nDiscovering services (this may take a moment)...")
    for d in devices:
        if d.name is None:
            continue
        try:
            async with BleakClient(d.address, timeout=5) as client:
                services = client.services
                print(f"\n{d.name} ({d.address}):")
                for svc in services:
                    print(f"  Service: {svc.uuid}")
                    for char in svc.characteristics:
                        props = char.properties
                        props_str = ",".join(props) if props else "none"
                        print(f"    Char: {char.uuid}  [{props_str}]")
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  {d.name} ({d.address}): {e}")


asyncio.run(scan())
