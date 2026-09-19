import platform
import sys
import os

try:
  import psutil
except ImportError:
    psutil = None


def get_system_info():
    """
    Return basic information about the current computer.
    """

    info = {
        "operating_system": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version.split()[0],
        "cpu_cores": os.cpu_count(),
    }

    if psutil:

        memory = psutil.virtual_memory()

        info["ram_total_gb"] = round(
            memory.total / (1024 ** 3),
            2
        )

        info["ram_available_gb"] = round(
            memory.available / (1024 ** 3),
            2
        )

        info["ram_usage_percent"] = memory.percent

        info["cpu_usage_percent"] = psutil.cpu_percent(
            interval=0.5
        )

    else:

        info["ram_info"] = (
            "Install psutil for RAM and CPU usage."
        )

    return info