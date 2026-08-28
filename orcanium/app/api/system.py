"""System information endpoints — real hardware/OS metrics."""

import logging
import os
import shutil
import time
from typing import Any, Dict

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_cpu_info() -> Dict[str, Any]:
    """Return CPU count and load average."""
    cpu_count = os.cpu_count() or 1
    try:
        load_avg = os.getloadavg()
        load_pct = round((load_avg[0] / cpu_count) * 100, 1)
    except OSError:
        load_avg = (0.0, 0.0, 0.0)
        load_pct = 0.0

    return {
        "cores": cpu_count,
        "load_avg": {
            "1m": round(load_avg[0], 2),
            "5m": round(load_avg[1], 2),
            "15m": round(load_avg[2], 2),
        },
        "usage_pct": min(load_pct, 100.0),
    }


def _get_memory_info() -> Dict[str, Any]:
    """Return memory info using /proc/meminfo (Linux) or vm_stat (macOS)."""
    try:
        # Try psutil first (best accuracy)
        import psutil

        mem = psutil.virtual_memory()
        return {
            "total_bytes": mem.total,
            "available_bytes": mem.available,
            "used_bytes": mem.used,
            "usage_pct": round(mem.percent, 1),
        }
    except ImportError:
        pass

    # Fallback: parse /proc/meminfo on Linux
    try:
        with open("/proc/meminfo") as f:
            data = f.read()
        lines = data.strip().split("\n")
        meminfo = {}
        for line in lines:
            parts = line.split(":")
            if len(parts) == 2:
                key = parts[0].strip()
                val = parts[1].strip().split()[0]
                meminfo[key] = int(val) * 1024  # kB to bytes
        total = meminfo.get("MemTotal", 0)
        available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
        used = total - available
        pct = round((used / total) * 100, 1) if total > 0 else 0
        return {
            "total_bytes": total,
            "available_bytes": available,
            "used_bytes": used,
            "usage_pct": pct,
        }
    except Exception:
        pass

    # Fallback: macOS vm_stat
    try:
        import re
        import subprocess

        # Get total physical RAM from sysctl (always works on macOS)
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        total = int(result.stdout.strip())

        # Get page size and page counts from vm_stat
        result = subprocess.run(
            ["vm_stat"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        page_size = 16384  # default Apple Silicon page size
        free_pages = 0
        # Parse lines like "Pages free:  12345."
        for line in result.stdout.split("\n"):
            m = re.match(
                r"Pages\s+(free|active|speculative|wired)\s*:\s*(\d+)",
                line,
                re.IGNORECASE,
            )
            if m:
                key = m.group(1).lower()
                val = int(m.group(2))
                if key == "free":
                    free_pages = val
                elif key == "speculative":
                    free_pages += val

        available = free_pages * page_size
        used = total - available
        pct = round((used / total) * 100, 1) if total > 0 else 0
        return {
            "total_bytes": total,
            "available_bytes": available,
            "used_bytes": used,
            "usage_pct": pct,
        }
    except Exception:
        pass

    # Absolute last resort — signal unavailable instead of lying with disk data
    return {
        "total_bytes": 0,
        "available_bytes": 0,
        "used_bytes": 0,
        "usage_pct": 0.0,
    }


def _get_disk_info() -> Dict[str, Any]:
    """Return disk usage for the root partition."""
    try:
        usage = shutil.disk_usage("/")
        total_gb = round(usage.total / (1024**3), 1)
        used_gb = round(usage.used / (1024**3), 1)
        free_gb = round(usage.free / (1024**3), 1)
        pct = round((usage.used / usage.total) * 100, 1)
        return {
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "usage_pct": pct,
        }
    except Exception:
        return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "usage_pct": 0}


def _get_uptime() -> str:
    """Return human-readable uptime string."""
    try:
        if os.path.exists("/proc/uptime"):
            with open("/proc/uptime") as f:
                uptime_seconds = float(f.read().split()[0])
        else:
            # macOS: use boot time from sysctl
            import subprocess

            result = subprocess.run(
                ["sysctl", "-n", "kern.boottime"],
                capture_output=True,
                text=True,
            )
            # Output: { sec = 123456, usec = 789 } or "123456"
            import re

            match = re.search(r"sec = (\d+)", result.stdout)
            if match:
                boot_time = int(match.group(1))
                uptime_seconds = time.time() - boot_time
            else:
                uptime_seconds = 0
    except Exception:
        uptime_seconds = 0

    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    return f"{days}d {hours}h {minutes}m"


def _get_host_info() -> Dict[str, Any]:
    """Return OS and host name."""
    import platform

    return {
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "python": platform.python_version(),
    }


@router.get("/stats")
def get_system_stats():
    """Return real system hardware and OS metrics."""
    return {
        "host": _get_host_info(),
        "cpu": _get_cpu_info(),
        "memory": _get_memory_info(),
        "disk": _get_disk_info(),
        "uptime": _get_uptime(),
    }
