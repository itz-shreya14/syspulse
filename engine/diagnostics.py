import os
import tempfile
import psutil
from typing import Dict, Any, List

class SystemDoctor:
    """
    Intelligent diagnostics engine. Computes a composite health score (0-100)
    and provides real-time system recommendations and safe cache maintenance.
    """
    @staticmethod
    def evaluate(telemetry: Dict[str, Any], top_procs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates a 0-100 composite health score and generates actionable diagnostic alerts.
        """
        score = 100
        findings: List[Dict[str, str]] = []

        # 1. CPU Evaluation
        cpu_pct = telemetry.get("cpu", {}).get("overall_percent", 0.0)
        if cpu_pct > 90:
            score -= 30
            findings.append({
                "level": "critical",
                "title": "Severe CPU Bottleneck",
                "message": f"CPU usage is spiking at {cpu_pct}%. Active tasks may be throttling."
            })
        elif cpu_pct > 75:
            score -= 15
            findings.append({
                "level": "warning",
                "title": "Elevated CPU Load",
                "message": f"CPU usage is at {cpu_pct}%. Monitor background compute processes."
            })
        else:
            findings.append({
                "level": "info",
                "title": "CPU Frequency & Load Nominal",
                "message": f"Processor is operating comfortably at {cpu_pct}%."
            })

        # 2. Memory Evaluation
        ram_pct = telemetry.get("memory", {}).get("ram", {}).get("percent", 0.0)
        swap_pct = telemetry.get("memory", {}).get("swap", {}).get("percent", 0.0)

        if ram_pct > 90:
            score -= 30
            findings.append({
                "level": "critical",
                "title": "Critical Memory Pressure",
                "message": f"RAM is {ram_pct}% full. System paging may cause stuttering."
            })
        elif ram_pct > 80:
            score -= 15
            findings.append({
                "level": "warning",
                "title": "High Memory Footprint",
                "message": f"RAM utilization is at {ram_pct}%. Consider closing inactive apps."
            })
        else:
            findings.append({
                "level": "info",
                "title": "Memory Buffer Healthy",
                "message": f"RAM utilization is stable at {ram_pct}%."
            })

        if swap_pct > 60:
            score -= 10
            findings.append({
                "level": "warning",
                "title": "Heavy Swap/Pagefile Usage",
                "message": f"Swap memory is {swap_pct}% utilized, indicating physical RAM exhaustion."
            })

        # 3. Disk Evaluation
        disks = telemetry.get("disks", [])
        for d in disks:
            pct = d.get("percent", 0)
            if pct > 92:
                score -= 15
                findings.append({
                    "level": "critical",
                    "title": f"Disk Near Capacity ({d.get('mountpoint')})",
                    "message": f"Drive is {pct}% full ({d.get('free_gb')} GB free). Performance may degrade."
                })
            elif pct > 85:
                score -= 8
                findings.append({
                    "level": "warning",
                    "title": f"Disk Capacity Warning ({d.get('mountpoint')})",
                    "message": f"Drive has reached {pct}% capacity ({d.get('free_gb')} GB free)."
                })

        # 4. Rogue Process Check
        high_cpu_procs = [p for p in top_procs if p.get("cpu_percent", 0) > 25]
        if high_cpu_procs:
            names = ", ".join([f"{p['name']} ({p['cpu_percent']}%)" for p in high_cpu_procs[:3]])
            findings.append({
                "level": "warning",
                "title": "Resource-Intensive Processes Detected",
                "message": f"High CPU consumption from: {names}."
            })

        # 5. Battery State
        battery = telemetry.get("battery", {})
        if battery.get("has_battery") and not battery.get("power_plugged") and battery.get("percent", 100) < 20:
            score -= 10
            findings.append({
                "level": "warning",
                "title": "Low Battery Level",
                "message": f"Battery is at {battery.get('percent')}%. Connect charger to prevent shutdown."
            })

        # Bound score between 0 and 100
        score = max(5, min(100, score))

        # Status text & visual tier
        if score >= 90:
            status_text = "OPTIMAL"
            status_color = "emerald"
        elif score >= 75:
            status_text = "GOOD"
            status_color = "cyan"
        elif score >= 50:
            status_text = "FAIR"
            status_color = "amber"
        else:
            status_text = "NEEDS ATTENTION"
            status_color = "rose"

        return {
            "health_score": score,
            "status_text": status_text,
            "status_color": status_color,
            "findings": findings
        }

    @staticmethod
    def get_cache_summary() -> Dict[str, Any]:
        """Scans user temporary cache directory to evaluate purgeable junk files."""
        temp_dir = tempfile.gettempdir()
        total_bytes = 0
        file_count = 0

        try:
            for entry in os.scandir(temp_dir):
                if entry.is_file(follow_symlinks=False):
                    try:
                        total_bytes += entry.stat().st_size
                        file_count += 1
                    except (PermissionError, OSError):
                        pass
        except Exception:
            pass

        return {
            "temp_dir": temp_dir,
            "file_count": file_count,
            "size_mb": round(total_bytes / (1024 * 1024), 1)
        }

    @staticmethod
    def clean_cache() -> Dict[str, Any]:
        """Safely removes un-locked files from the user temp directory."""
        temp_dir = tempfile.gettempdir()
        freed_bytes = 0
        deleted_count = 0

        try:
            for entry in os.scandir(temp_dir):
                if entry.is_file(follow_symlinks=False):
                    try:
                        size = entry.stat().st_size
                        os.remove(entry.path)
                        freed_bytes += size
                        deleted_count += 1
                    except (PermissionError, OSError):
                        # Skip locked or in-use files safely
                        continue
        except Exception as e:
            return {"success": False, "message": str(e), "freed_mb": 0.0}

        freed_mb = round(freed_bytes / (1024 * 1024), 1)
        return {
            "success": True,
            "message": f"Cleaned {deleted_count} files, freeing {freed_mb} MB of disk space.",
            "freed_mb": freed_mb
        }
