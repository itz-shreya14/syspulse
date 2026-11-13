"""
⚡ SysPulse Standalone Client Agent
Zero-configuration hardware telemetry streamer for remote computers.
Gathers local OS metrics and streams them via WebSocket to the cloud hub.
"""
import sys
import os
import time
import json
import socket
import asyncio
import argparse
import platform
from datetime import datetime

try:
    import psutil
except ImportError:
    print("[!] 'psutil' is required. Run: pip install psutil websockets")
    sys.exit(1)

try:
    import websockets
except ImportError:
    print("[!] 'websockets' is required. Run: pip install websockets")
    sys.exit(1)

BANNER = r"""
  ____             ____        _              _                    _   
 / ___| _   _ ___ |  _ \ _   _| |___  ___    / \   __ _  ___ _ __ | |_ 
 \___ \| | | / __|| |_) | | | | / __|/ _ \  / _ \ / _` |/ _ \ '_ \| __|
  ___) | |_| \__ \|  __/| |_| | \__ \  __/ / ___ \ (_| |  __/ | | | |_ 
 |____/ \__, |___/|_|    \__,_|_|___/\___|/_/   \_\__, |\___|_| |_|\__|
        |___/                                     |___/                
  >> Self-Contained Remote Hardware Streamer <<
"""

class StandaloneCollector:
    """Lightweight, self-contained telemetry collector."""
    def __init__(self):
        self.boot_time = psutil.boot_time()
        self.last_poll_time = time.time()
        
        # Prime non-blocking CPU
        psutil.cpu_percent(interval=None, percpu=True)
        psutil.cpu_percent(interval=None)

        try:
            net = psutil.net_io_counters()
            self.last_net_sent = net.bytes_sent
            self.last_net_recv = net.bytes_recv
        except Exception:
            self.last_net_sent, self.last_net_recv = 0, 0

        try:
            disk = psutil.disk_io_counters()
            self.last_disk_read = disk.read_bytes if disk else 0
            self.last_disk_write = disk.write_bytes if disk else 0
        except Exception:
            self.last_disk_read, self.last_disk_write = 0, 0

    def get_system_info(self):
        return {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "processor": platform.processor(),
            "physical_cores": psutil.cpu_count(logical=False) or 1,
            "logical_cores": psutil.cpu_count(logical=True) or 1
        }

    def collect(self):
        now = time.time()
        dt = max(now - self.last_poll_time, 0.001)
        self.last_poll_time = now

        # CPU
        cpu_overall = psutil.cpu_percent(interval=None)
        cpu_cores = psutil.cpu_percent(interval=None, percpu=True)
        freq = psutil.cpu_freq()

        # RAM & Swap
        vmem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Differential Disk I/O
        disk_read_kbs, disk_write_kbs = 0.0, 0.0
        try:
            d = psutil.disk_io_counters()
            if d:
                disk_read_kbs = max(0.0, (d.read_bytes - self.last_disk_read) / dt / 1024)
                disk_write_kbs = max(0.0, (d.write_bytes - self.last_disk_write) / dt / 1024)
                self.last_disk_read, self.last_disk_write = d.read_bytes, d.write_bytes
        except Exception:
            pass

        # Differential Net I/O
        net_up_kbs, net_down_kbs = 0.0, 0.0
        try:
            n = psutil.net_io_counters()
            if n:
                net_up_kbs = max(0.0, (n.bytes_sent - self.last_net_sent) / dt / 1024)
                net_down_kbs = max(0.0, (n.bytes_recv - self.last_net_recv) / dt / 1024)
                self.last_net_sent, self.last_net_recv = n.bytes_sent, n.bytes_recv
        except Exception:
            pass

        # Storage partitions
        disks = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / (1024 ** 3), 1),
                    "used_gb": round(usage.used / (1024 ** 3), 1),
                    "free_gb": round(usage.free / (1024 ** 3), 1),
                    "percent": round(usage.percent, 1)
                })
            except Exception:
                continue

        # Battery
        battery = psutil.sensors_battery()
        if battery:
            time_left_str = "Plugged In" if battery.power_plugged else "On Battery"
            if not battery.power_plugged and battery.secsleft and 0 < battery.secsleft < 86400 * 3:
                h = battery.secsleft // 3600
                m = (battery.secsleft % 3600) // 60
                time_left_str = f"{h}h {m}m left"

            battery_data = {
                "has_battery": True,
                "percent": round(battery.percent, 1),
                "power_plugged": battery.power_plugged,
                "status_text": time_left_str
            }
        else:
            battery_data = {
                "has_battery": False,
                "percent": 100.0,
                "power_plugged": True,
                "status_text": "AC Power"
            }

        # Uptime
        uptime_secs = int(time.time() - self.boot_time)
        days = uptime_secs // 86400
        hours = (uptime_secs % 86400) // 3600
        mins = (uptime_secs % 3600) // 60
        uptime_formatted = f"{days}d {hours}h {mins}m" if days > 0 else f"{hours}h {mins}m"

        # Calculate composite health score
        score = 100
        if cpu_overall > 85: score -= 25
        elif cpu_overall > 70: score -= 15
        if vmem.percent > 90: score -= 25
        elif vmem.percent > 80: score -= 15
        score = max(10, min(100, score))
        status_text = "OPTIMAL" if score >= 85 else ("GOOD" if score >= 70 else "NEEDS ATTENTION")
        status_color = "emerald" if score >= 85 else ("cyan" if score >= 70 else "amber")

        return {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "uptime_formatted": uptime_formatted,
            "cpu": {
                "overall_percent": round(cpu_overall, 1),
                "per_core_percent": [round(c, 1) for c in cpu_cores],
                "current_freq_mhz": round(freq.current, 1) if freq else None
            },
            "memory": {
                "ram": {
                    "total_gb": round(vmem.total / (1024 ** 3), 2),
                    "used_gb": round(vmem.used / (1024 ** 3), 2),
                    "percent": round(vmem.percent, 1)
                },
                "swap": {
                    "percent": round(swap.percent, 1)
                }
            },
            "disks": disks,
            "io": {
                "disk_read_kbs": round(disk_read_speed_kbs, 1),
                "disk_write_kbs": round(disk_write_speed_kbs, 1),
                "net_upload_kbs": round(net_up_kbs, 1),
                "net_download_kbs": round(net_down_kbs, 1)
            },
            "battery": battery_data,
            "health": {
                "score": score,
                "status": status_text,
                "color": status_color
            }
        }

def get_top_processes(limit=8):
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
        try:
            mem = p.info.get('memory_info')
            procs.append({
                "pid": p.info['pid'],
                "name": p.info.get('name') or "Unknown",
                "cpu_percent": round(p.info.get('cpu_percent') or 0.0, 1),
                "memory_mb": round((mem.rss / (1024 * 1024)), 1) if mem else 0.0,
                "status": p.info.get('status') or "running",
                "is_protected": False
            })
        except Exception:
            continue
    procs.sort(key=lambda x: x["memory_mb"], reverse=True)
    return procs[:limit]

async def run_telemetry_stream(hub_url: str, pin: str):
    print(BANNER)
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
    print(f"[*] Connecting to:    {target_ws}\n")

    collector = StandaloneCollector()
    sys_info = collector.get_system_info()
    hostname = sys_info.get('hostname', 'Remote Laptop')
    print(f"[+] Local Machine: {hostname} ({sys_info.get('os')} {sys_info.get('os_release')})")
    print(f"[+] Processor:     {sys_info.get('logical_cores')} Cores ({sys_info.get('processor', 'CPU')[:35]})\n")

    backoff = 2
    while True:
        try:
            print(f"[*] Connecting to SysPulse Cloud Hub...")
            async with websockets.connect(target_ws) as ws:
                print(f"[✔] Successfully Paired with PIN {pin}!")
                print(f"[✔] Streaming live telemetry of THIS machine to your browser... (Ctrl+C to stop)\n")
                backoff = 2
                tick = 0

                while True:
                    telemetry_data = collector.collect()
                    top_procs = get_top_processes(limit=8)

                    payload = {
                        "type": "telemetry_tick",
                        "device_id": pin,
                        "device_name": hostname,
                        "timestamp": telemetry_data["timestamp"],
                        "uptime": telemetry_data["uptime_formatted"],
                        "cpu": telemetry_data["cpu"],
                        "memory": telemetry_data["memory"],
                        "disks": telemetry_data["disks"],
                        "io": telemetry_data["io"],
                        "battery": telemetry_data["battery"],
                        "health": telemetry_data["health"],
                        "top_processes": top_procs
                    }

                    await ws.send(json.dumps(payload))
                    tick += 1

                    cpu_val = telemetry_data["cpu"]["overall_percent"]
                    ram_val = telemetry_data["memory"]["ram"]["percent"]
                    bat_val = telemetry_data["battery"].get("percent", "--")

                    sys.stdout.write(
                        f"\r[{telemetry_data['timestamp']}] Frame #{tick:04d} | CPU: {cpu_val:4.1f}% | RAM: {ram_val:4.1f}% | Bat: {bat_val}% | Health: {telemetry_data['health']['score']}%  "
                    )
                    sys.stdout.flush()
                    await asyncio.sleep(1.0)

        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            print(f"\n[!] Connection dropped ({e}). Reconnecting in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 16)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"\n[!] Unexpected error: {e}. Retrying in {backoff}s...")
            await asyncio.sleep(backoff)

def main():
    parser = argparse.ArgumentParser(description="SysPulse Standalone Remote Telemetry Agent")
    parser.add_argument("--hub", type=str, default="http://127.0.0.1:8000", help="SysPulse Cloud Hub URL")
    parser.add_argument("--pin", type=str, default="", help="6-digit device pairing PIN")

    args = parser.parse_args()
    hub_url = args.hub
    pin = args.pin.strip()

    if not pin:
        print(BANNER)
        print("To monitor THIS computer on your SysPulse web dashboard:")
        print("1. Open the dashboard in your browser.")
        print("2. Click 'Pair Device' in the header to get your 6-digit PIN.")
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
        print("\n[+] Agent stopped.")

if __name__ == "__main__":
    main()
