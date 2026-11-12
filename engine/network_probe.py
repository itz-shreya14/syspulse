import socket
import time
import psutil
from typing import List, Dict, Any, Optional

class NetworkProbe:
    """
    Analyzes active network sockets, network interfaces, and measures connection latency.
    """
    @staticmethod
    def get_active_connections(limit: int = 50) -> List[Dict[str, Any]]:
        """
        Inspects open network sockets, associating each with process name and status.
        """
        results: List[Dict[str, Any]] = []
        try:
            conns = psutil.net_connections(kind='inet')
        except (psutil.AccessDenied, Exception):
            return results

        # Cache process names by PID to avoid repeated process lookups
        proc_names: Dict[int, str] = {}

        for c in conns:
            try:
                laddr_str = f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "None"
                raddr_str = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "None"
                
                # Protocol
                proto = "TCP" if c.type == socket.SOCK_STREAM else "UDP"
                status = c.status if c.status else ("LISTENING" if proto == "UDP" else "ESTABLISHED")

                # Process name lookup
                pname = "System / Unknown"
                if c.pid:
                    if c.pid not in proc_names:
                        try:
                            proc_names[c.pid] = psutil.Process(c.pid).name()
                        except Exception:
                            proc_names[c.pid] = "N/A"
                    pname = proc_names[c.pid]

                results.append({
                    "protocol": proto,
                    "local_address": laddr_str,
                    "remote_address": raddr_str,
                    "status": status,
                    "pid": c.pid or 0,
                    "process_name": pname
                })
            except Exception:
                continue

        # Sort with ESTABLISHED first, then LISTEN
        results.sort(key=lambda x: (0 if x["status"] == "ESTABLISHED" else 1, x["remote_address"] == "None"))
        return results[:limit]

    @staticmethod
    def get_interfaces() -> List[Dict[str, Any]]:
        """Returns details on physical/virtual network adapters."""
        interfaces: List[Dict[str, Any]] = []
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for name, addr_list in addrs.items():
            ipv4 = "N/A"
            mac = "N/A"
            for a in addr_list:
                if a.family == socket.AF_INET:
                    ipv4 = a.address
                elif hasattr(psutil, 'AF_LINK') and a.family == psutil.AF_LINK:
                    mac = a.address
            
            stat = stats.get(name)
            is_up = stat.isup if stat else False
            speed_mbps = stat.speed if stat else 0

            # Only include interfaces that are UP or have valid IPv4
            if is_up or ipv4 != "N/A":
                interfaces.append({
                    "name": name,
                    "ipv4": ipv4,
                    "mac": mac,
                    "is_up": is_up,
                    "speed_mbps": speed_mbps
                })

        return interfaces

    @staticmethod
    def measure_latency(host: str = "1.1.1.1", port: int = 80, timeout: float = 1.0) -> Optional[float]:
        """
        Measures round-trip TCP connection handshake latency in milliseconds.
        Uses pure Python sockets without requiring OS ping permissions.
        """
        start = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            latency_ms = (time.perf_counter() - start) * 1000.0
            sock.close()
            return round(latency_ms, 1)
        except Exception:
            return None

