"""
core/system_stats.py
Real system metrics for the dashboard widgets, using psutil.
"""

import psutil


def get_system_stats():
    net = psutil.net_io_counters()
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "ram_percent": psutil.virtual_memory().percent,
        "ram_used_gb": round(psutil.virtual_memory().used / (1024 ** 3), 2),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "packets_sent": net.packets_sent,
        "packets_recv": net.packets_recv,
        "bytes_sent_mb": round(net.bytes_sent / (1024 ** 2), 2),
        "bytes_recv_mb": round(net.bytes_recv / (1024 ** 2), 2),
    }