import time
import platform
import psutil
from datetime import datetime
from typing import Dict, Any, List

class TelemetryCollector:
    """
    High-performance, non-blocking telemetry collector for host system metrics.
    Calculates differential rates for network and disk I/O.
    """
    def __init__(self):
        self.boot_time = psutil.boot_time()
        self.system_info = self._get_static_system_info()
        
        # Prime psutil.cpu_percent so subsequent calls with interval=None return valid non-blocking metrics
        psutil.cpu_percent(interval=None, percpu=True)
        psutil.cpu_percent(interval=None)
        
        # Initialize time and counters for rate calculation
        self.last_poll_time = time.time()
        
        try:
            net_io = psutil.net_io_counters()
            self.last_net_bytes_sent = net_io.bytes_sent
            self.last_net_bytes_recv = net_io.bytes_recv
        except Exception:
            self.last_net_bytes_sent = 0
            self.last_net_bytes_recv = 0
            
        try:
            disk_io = psutil.disk_io_counters()
            self.last_disk_read_bytes = disk_io.read_bytes if disk_io else 0
            self.last_disk_write_bytes = disk_io.write_bytes if disk_io else 0
        except Exception:
            self.last_disk_read_bytes = 0
            self.last_disk_write_bytes = 0

    def _get_static_system_info(self) -> Dict[str, Any]:
        """Fetch hardware and OS specifications that don't change dynamically."""
        return {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "processor": platform.processor(),
            "physical_cores": psutil.cpu_count(logical=False) or 1,
            "logical_cores": psutil.cpu_count(logical=True) or 1,
            "boot_time_iso": datetime.fromtimestamp(self.boot_time).strftime("%Y-%m-%d %H:%M:%S")
        }

    def collect(self) -> Dict[str, Any]:
        """Collect a full dynamic telemetry snapshot."""
        now = time.time()
        dt = max(now - self.last_poll_time, 0.001)
        self.last_poll_time = now

        # --- 1. CPU Telemetry ---
        cpu_overall = psutil.cpu_percent(interval=None)
        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
        freq = psutil.cpu_freq()
        cpu_metrics = {
            "overall_percent": round(cpu_overall, 1),
            "per_core_percent": [round(c, 1) for c in cpu_per_core],
            "current_freq_mhz": round(freq.current, 1) if freq else None,
            "min_freq_mhz": round(freq.min, 1) if freq and freq.min > 0 else None,
            "max_freq_mhz": round(freq.max, 1) if freq and freq.max > 0 else None
        }

        # --- 2. Memory Telemetry ---
        vmem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        memory_metrics = {
            "ram": {
                "total_gb": round(vmem.total / (1024 ** 3), 2),
                "used_gb": round(vmem.used / (1024 ** 3), 2),
                "available_gb": round(vmem.available / (1024 ** 3), 2),
                "percent": round(vmem.percent, 1)
            },
            "swap": {
                "total_gb": round(swap.total / (1024 ** 3), 2),
                "used_gb": round(swap.used / (1024 ** 3), 2),
                "free_gb": round(swap.free / (1024 ** 3), 2),
                "percent": round(swap.percent, 1)
            }
        }

        # --- 3. Disk Partitions & I/O Rate ---
        disks = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / (1024 ** 3), 1),
                    "used_gb": round(usage.used / (1024 ** 3), 1),
                    "free_gb": round(usage.free / (1024 ** 3), 1),
                    "percent": round(usage.percent, 1)
                })
            except (PermissionError, OSError):
                continue

        # Disk I/O delta
        disk_read_speed_kbs = 0.0
        disk_write_speed_kbs = 0.0
        try:
            current_disk_io = psutil.disk_io_counters()
            if current_disk_io:
                disk_read_speed_kbs = max(0.0, (current_disk_io.read_bytes - self.last_disk_read_bytes) / dt / 1024)
                disk_write_speed_kbs = max(0.0, (current_disk_io.write_bytes - self.last_disk_write_bytes) / dt / 1024)
                self.last_disk_read_bytes = current_disk_io.read_bytes
                self.last_disk_write_bytes = current_disk_io.write_bytes
        except Exception:
            pass

        # --- 4. Network Throughput Rate ---
        net_upload_kbs = 0.0
        net_download_kbs = 0.0
        try:
            current_net_io = psutil.net_io_counters()
            if current_net_io:
                net_upload_kbs = max(0.0, (current_net_io.bytes_sent - self.last_net_bytes_sent) / dt / 1024)
                net_download_kbs = max(0.0, (current_net_io.bytes_recv - self.last_net_bytes_recv) / dt / 1024)
                self.last_net_bytes_sent = current_net_io.bytes_sent
                self.last_net_bytes_recv = current_net_io.bytes_recv
        except Exception:
            pass

        # --- 5. Battery & Power Status ---
        battery = psutil.sensors_battery()
        if battery:
            time_left_str = "Calculating..."
            if battery.power_plugged:
                time_left_str = "Plugged In (Charging)"
            elif (
                battery.secsleft is not None 
                and battery.secsleft != psutil.POWER_TIME_UNLIMITED 
                and 0 < battery.secsleft < 86400 * 3
            ):
                hours = battery.secsleft // 3600
                mins = (battery.secsleft % 3600) // 60
                time_left_str = f"{hours}h {mins}m remaining"
            else:
                time_left_str = "On Battery (Estimating)"

            battery_metrics = {
                "has_battery": True,
                "percent": round(battery.percent, 1),
                "power_plugged": battery.power_plugged,
                "status_text": time_left_str
            }
        else:
            battery_metrics = {
                "has_battery": False,
                "percent": 100.0,
                "power_plugged": True,
                "status_text": "AC Power (Desktop)"
            }

        # --- 6. Uptime ---
        uptime_secs = int(time.time() - self.boot_time)
        days = uptime_secs // 86400
        hours = (uptime_secs % 86400) // 3600
        mins = (uptime_secs % 3600) // 60
        uptime_formatted = f"{days}d {hours}h {mins}m" if days > 0 else f"{hours}h {mins}m"

        return {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "uptime_seconds": uptime_secs,
            "uptime_formatted": uptime_formatted,
            "system": self.system_info,
            "cpu": cpu_metrics,
            "memory": memory_metrics,
            "disks": disks,
            "io": {
                "disk_read_kbs": round(disk_read_speed_kbs, 1),
                "disk_write_kbs": round(disk_write_speed_kbs, 1),
                "net_upload_kbs": round(net_upload_kbs, 1),
                "net_download_kbs": round(net_download_kbs, 1)
            },
            "battery": battery_metrics
        }
