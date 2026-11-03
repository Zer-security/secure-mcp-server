import ipaddress
import socket

import psutil


def network_interfaces() -> str:
    """Menampilkan interface jaringan dan alamat IPv4-nya (cross-platform)."""
    lines = []

    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family != socket.AF_INET:
                continue

            prefix = None
            if addr.netmask:
                try:
                    prefix = ipaddress.IPv4Network(
                        f"0.0.0.0/{addr.netmask}", strict=False
                    ).prefixlen
                except ValueError:
                    prefix = None

            if prefix is not None:
                lines.append(f"{interface}: {addr.address}/{prefix}")
            else:
                lines.append(f"{interface}: {addr.address}")

    return "\n".join(lines) if lines else "Tidak ada interface IPv4."
