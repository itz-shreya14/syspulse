"""
⚡ SysPulse Client Agent
Lightweight, cross-platform hardware telemetry streamer.
Gathers local OS metrics and streams them via WebSocket to the cloud hub.
"""
import sys
import time
import json
import asyncio
import argparse
import websockets

from engine.telemetry import TelemetryCollector
from engine.process_manager import ProcessManager
from engine.diagnostics import SystemDoctor

BANNER = r"""
  ____             ____        _              _                    _   
 / ___| _   _ ___ |  _ \ _   _| |___  ___    / \   __ _  ___ _ __ | |_ 
 \___ \| | | / __|| |_) | | | | / __|/ _ \  / _ \ / _` |/ _ \ '_ \| __|
  ___) | |_| \__ \|  __/| |_| | \__ \  __/ / ___ \ (_| |  __/ | | | |_ 
 |____/ \__, |___/|_|    \__,_|_|___/\___|/_/   \_\__, |\___|_| |_|\__|
        |___/                                     |___/                
  >> Device Telemetry Streamer <<
"""

async def run_telemetry_stream(hub_url: str, pin: str):
    print(BANNER)
    # Sanitize WebSocket URL
    ws_base = hub_url.strip().rstrip('/')
    if ws_base.startswith("https://"):
        ws_base = "wss://" + ws_base[8:]
    elif ws_base.startswith("http://"):
        ws_base = "ws://" + ws_base[7:]
    elif not ws_base.startswith("ws://") and not ws_base.startswith("wss://"):
        ws_base = "wss://" + ws_base

    target_ws = f"{ws_base}/ws/agent/{pin}"
    print(f"[*] Target Cloud Hub: {hub_url}")
    print(f"[*] Pairing with PIN: {pin}")
    print(f"[*] WebSocket URL:    {target_ws}")
    print(f"[*] Initializing local hardware sensor probes...\n")

    collector = TelemetryCollector()
    sys_info = collector.system_info
    print(f"[+] Local Machine: {sys_info.get('hostname')} ({sys_info.get('os')} {sys_info.get('os_release')})")
    print(f"[+] Hardware Cores: {sys_info.get('logical_cores')} Cores ({sys_info.get('processor', 'CPU')[:35]})\n")

    backoff = 2
    while True:
        try:
            print(f"[*] Connecting to SysPulse Cloud Hub...")
            async with websockets.connect(target_ws) as ws:
                print(f"[✔] Successfully Paired & Connected to Cloud Hub!")
                print(f"[✔] Streaming live telemetry to your friend's browser... (Press Ctrl+C to stop)\n")
                backoff = 2

                tick = 0
                while True:
                    telemetry_data = collector.collect()
                    top_procs = ProcessManager.get_processes(sort_by="cpu", limit=10)
                    health = SystemDoctor.evaluate(telemetry_data, top_procs)

                    payload = {
                        "type": "telemetry_tick",
                        "device_id": pin,
                        "device_name": sys_info.get('hostname', 'Remote Laptop'),
                        "timestamp": telemetry_data["timestamp"],
                        "uptime": telemetry_data["uptime_formatted"],
                        "cpu": telemetry_data["cpu"],
                        "memory": telemetry_data["memory"],
                        "io": telemetry_data["io"],
                        "battery": telemetry_data["battery"],
                        "health": {
                            "score": health["health_score"],
                            "status": health["status_text"],
                            "color": health["status_color"]
                        },
                        "top_processes": top_procs[:6]
                    }

                    await ws.send(json.dumps(payload))
                    tick += 1

                    cpu_val = telemetry_data["cpu"]["overall_percent"]
                    ram_val = telemetry_data["memory"]["ram"]["percent"]
                    bat_val = telemetry_data["battery"].get("percent", "--")

                    # Live terminal telemetry ticker
                    sys.stdout.write(
                        f"\r[{telemetry_data['timestamp']}] #Frames: {tick:04d} | CPU: {cpu_val:4.1f}% | RAM: {ram_val:4.1f}% | Bat: {bat_val}% | Health: {health['health_score']}% ({health['status_text']})  "
                    )
                    sys.stdout.flush()

                    await asyncio.sleep(1.0)

        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            print(f"\n[!] Connection lost: {e}. Retrying in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 16)
        except asyncio.CancelledError:
            print("\n[*] Stopping agent telemetry loop...")
            break
        except Exception as e:
            print(f"\n[!] Unexpected error: {e}. Retrying in {backoff}s...")
            await asyncio.sleep(backoff)

def main():
    parser = argparse.ArgumentParser(description="SysPulse Remote Telemetry Agent")
    parser.add_argument("--hub", type=str, default="http://127.0.0.1:8000", help="SysPulse Cloud Hub URL (e.g. https://syspulse-hub.onrender.com)")
    parser.add_argument("--pin", type=str, default="", help="6-digit device pairing PIN generated on web dashboard")

    args = parser.parse_args()

    hub_url = args.hub
    pin = args.pin.strip()

    if not pin:
        print(BANNER)
        print("To connect your machine to the SysPulse Dashboard:")
        print("1. Open the SysPulse Web Dashboard in your browser.")
        print("2. Click 'Pair Remote Device' to see your 6-digit PIN.")
        try:
            pin = input("\nEnter your 6-digit Device PIN (e.g. 482-901): ").strip()
        except KeyboardInterrupt:
            print("\nExiting.")
            sys.exit(0)

    if not pin:
        print("[!] Error: PIN cannot be empty.")
        sys.exit(1)

    try:
        asyncio.run(run_telemetry_stream(hub_url, pin))
    except KeyboardInterrupt:
        print("\n[+] Agent stopped by user.")

if __name__ == "__main__":
    main()
