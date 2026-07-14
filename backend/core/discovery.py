"""
core/discovery.py
Discovers live hosts on a subnet using a concurrent ping sweep.
This works without root/admin privileges on all major OSes.

MAC address + vendor lookup is BEST-EFFORT: it reads the OS's ARP cache
after pinging (arp -a). This only works reliably for devices on the SAME
local network segment as the machine running this code — that's a real
networking limitation, not a bug, and worth understanding for your resume
talking points.
"""

import ipaddress
import platform
import re
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor

# Small offline OUI (MAC prefix -> vendor) sample table.
# A production tool would use the full IEEE OUI database or an API.
OUI_VENDORS = {
    "00:1A:11": "Google",
    "3C:5A:B4": "Apple",
    "F4:5C:89": "Apple",
    "B8:27:EB": "Raspberry Pi Foundation",
    "00:50:56": "VMware",
    "08:00:27": "VirtualBox",
    "00:0C:29": "VMware",
    "DC:A6:32": "Raspberry Pi Foundation",
    "A4:83:E7": "Intel",
}


def _ping_host(ip: str) -> bool:
    param = "-n" if platform.system().lower() == "windows" else "-c"
    cmd = ["ping", param, "1", "-W", "1", str(ip)] if platform.system().lower() != "windows" \
        else ["ping", param, "1", "-w", "800", str(ip)]
    try:
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        return result.returncode == 0
    except Exception:
        return False


def _read_arp_table() -> dict:
    """Returns {ip: mac} from the OS ARP cache."""
    table = {}
    try:
        output = subprocess.check_output(["arp", "-a"], text=True, stderr=subprocess.DEVNULL)
        for line in output.splitlines():
            ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
            mac_match = re.search(r"([0-9A-Fa-f]{2}([:-][0-9A-Fa-f]{2}){5})", line)
            if ip_match and mac_match:
                table[ip_match.group(1)] = mac_match.group(1).upper().replace("-", ":")
    except Exception:
        pass
    return table


def _vendor_from_mac(mac: str) -> str:
    if not mac:
        return "Unknown"
    prefix = mac[:8].upper()
    return OUI_VENDORS.get(prefix, "Unknown Vendor")


def _hostname_for(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return "-"


def discover_network(cidr: str, max_hosts: int = 254):
    """
    cidr: e.g. '192.168.1.0/24'
    Returns a list of discovered device dicts.
    """
    network = ipaddress.ip_network(cidr, strict=False)
    hosts = list(network.hosts())[:max_hosts]

    alive = []
    with ThreadPoolExecutor(max_workers=50) as pool:
        results = pool.map(lambda ip: (str(ip), _ping_host(str(ip))), hosts)
        alive = [ip for ip, ok in results if ok]

    arp_table = _read_arp_table()
    devices = []
    for ip in alive:
        mac = arp_table.get(ip, "")
        devices.append({
            "ip": ip,
            "mac": mac or "Unknown",
            "vendor": _vendor_from_mac(mac),
            "hostname": _hostname_for(ip),
            "status": "online",
            "last_seen": "just now",
        })
    return devices