"""
core/scanner.py
Real TCP port scanning using Python sockets — no external tool required.
If nmap + python-nmap are installed on the host machine, OS detection and
service-version detection get an optional upgrade (see try_nmap_enrich).
"""

import socket
import time

# port -> (service, risk_level, description)
PORT_INTEL = {
    21:   ("FTP", "high", "Unencrypted file transfer — credentials sent in plaintext."),
    22:   ("SSH", "medium", "Remote shell access. Should be key-based auth only, not password."),
    23:   ("Telnet", "critical", "Unencrypted remote login. Should never be exposed."),
    25:   ("SMTP", "medium", "Mail relay. Check for open relay misconfiguration."),
    53:   ("DNS", "medium", "DNS service. Watch for zone transfer misconfig."),
    80:   ("HTTP", "medium", "Unencrypted web traffic. Should redirect to HTTPS."),
    110:  ("POP3", "high", "Unencrypted mail retrieval protocol."),
    111:  ("RPCbind", "high", "Often abused for enumeration/DDoS reflection."),
    135:  ("MSRPC", "high", "Windows RPC — common lateral movement target."),
    139:  ("NetBIOS", "high", "Legacy Windows file sharing — high attack surface."),
    143:  ("IMAP", "high", "Unencrypted mail access protocol."),
    443:  ("HTTPS", "low", "Encrypted web traffic — verify certificate validity separately."),
    445:  ("SMB", "critical", "Windows file sharing — frequent ransomware/worm target (e.g. EternalBlue)."),
    993:  ("IMAPS", "low", "Encrypted mail access."),
    995:  ("POP3S", "low", "Encrypted mail retrieval."),
    1433: ("MSSQL", "high", "Database service — should not be internet-facing."),
    1521: ("Oracle DB", "high", "Database service — should not be internet-facing."),
    3306: ("MySQL", "high", "Database service — should not be internet-facing."),
    3389: ("RDP", "critical", "Remote Desktop — top target for brute force and ransomware."),
    5432: ("PostgreSQL", "high", "Database service — should not be internet-facing."),
    5900: ("VNC", "critical", "Remote desktop protocol, frequently misconfigured with no auth."),
    6379: ("Redis", "critical", "In-memory DB, historically exposed with no auth by default."),
    8080: ("HTTP-Alt", "medium", "Alternate web/proxy port, often an admin panel."),
    8443: ("HTTPS-Alt", "low", "Alternate encrypted web port."),
    27017: ("MongoDB", "critical", "Database service, historically exposed with no auth."),
}

QUICK_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 8080]
FULL_PORTS = list(range(1, 1025)) + [1433, 1521, 3306, 3389, 5432, 5900, 6379, 8080, 8443, 27017]


def parse_port_spec(spec: str):
    """Turns '20-25,80,443' into a sorted list of unique ints."""
    ports = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start, end = chunk.split("-")
            ports.update(range(int(start), int(end) + 1))
        else:
            ports.add(int(chunk))
    return sorted(p for p in ports if 1 <= p <= 65535)


def resolve_target(target: str) -> str:
    return socket.gethostbyname(target)


def grab_banner(ip: str, port: int, timeout: float = 0.8) -> str:
    """Best-effort banner grab. Returns empty string if nothing comes back."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((ip, port))
            # HTTP needs a nudge, most others send a banner on connect
            if port in (80, 8080):
                s.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
            banner = s.recv(256).decode(errors="ignore").strip()
            return banner.split("\n")[0][:120]
    except Exception:
        return ""


def scan_single_port(ip: str, port: int, grab_banners: bool, timeout: float = 0.5):
    start = time.time()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    result = sock.connect_ex((ip, port))
    latency_ms = round((time.time() - start) * 1000, 1)
    sock.close()

    is_open = result == 0
    service, risk, desc = PORT_INTEL.get(port, ("Unknown", "low", "Unclassified service."))

    banner = ""
    if is_open and grab_banners:
        banner = grab_banner(ip, port)

    return {
        "port": port,
        "protocol": "TCP",
        "state": "open" if is_open else "closed",
        "service": service,
        "version": banner if banner else "-",
        "banner": banner,
        "risk": risk if is_open else "none",
        "description": desc if is_open else "",
        "latency_ms": latency_ms,
    }