import asyncio

from server import mcp
from tools import (
    kali_info,
    system_status,
    disk_status,
    memory_status,
    network_status,
    network_interfaces,
)


EXPECTED_TOOL_NAMES = {
    "kali_info",
    "system_status",
    "disk_status",
    "memory_status",
    "network_status",
    "network_interfaces",
    "read_text_file",
}


def test_kali_info():
    result = kali_info()
    assert "Kali MCP Server aktif." in result


def test_system_status():
    result = system_status()
    assert "OS:" in result
    assert "Hostname:" in result
    assert "Python:" in result


def test_disk_status():
    result = disk_status()
    assert "Disk total:" in result
    assert "Disk terpakai:" in result
    assert "Disk bebas:" in result


def test_disk_status_uses_disk_usage_result(monkeypatch):
    from tools import system_tools

    monkeypatch.setattr(
        "shutil.disk_usage",
        lambda path: (10 * 1024**3, 4 * 1024**3, 6 * 1024**3),
    )

    result = system_tools.disk_status()

    assert "Disk total: 10.0 GB" in result
    assert "Disk terpakai: 4.0 GB" in result
    assert "Disk bebas: 6.0 GB" in result


def test_memory_status():
    result = memory_status()
    assert "RAM total:" in result
    assert "RAM terpakai:" in result
    assert "RAM tersedia:" in result


def test_memory_status_parses_meminfo(monkeypatch):
    from tools import system_tools

    class FakeVirtualMemory:
        total = 2097152 * 1024
        available = 1572864 * 1024
        used = total - available

    monkeypatch.setattr(
        system_tools.psutil, "virtual_memory", lambda: FakeVirtualMemory()
    )

    result = system_tools.memory_status()

    assert "RAM total: 2.0 GB" in result
    assert "RAM terpakai: 0.5 GB" in result
    assert "RAM tersedia: 1.5 GB" in result


def test_network_status():
    result = network_status()
    assert "Hostname:" in result
    assert "IP lokal:" in result


def test_network_status_handles_resolution_error(monkeypatch):
    from tools import system_tools

    monkeypatch.setattr(
        "socket.gethostname",
        lambda: "test-host",
    )

    def raise_resolution_error(hostname):
        import socket
        raise socket.gaierror("resolution failed")

    monkeypatch.setattr(
        "socket.gethostbyname",
        raise_resolution_error,
    )

    result = system_tools.network_status()

    assert result == "Hostname: test-host\nIP lokal: Tidak tersedia"


def test_network_interfaces_uses_psutil(monkeypatch):
    import socket as socket_module

    from tools import network_tools

    class FakeAddr:
        family = socket_module.AF_INET
        address = "127.0.0.1"
        netmask = "255.0.0.0"

    monkeypatch.setattr(
        network_tools.psutil,
        "net_if_addrs",
        lambda: {"lo": [FakeAddr()]},
    )

    result = network_tools.network_interfaces()

    assert result == "lo: 127.0.0.1/8"


def test_network_interfaces():
    result = network_interfaces()

    assert isinstance(result, str)
    assert result.strip()

    for line in result.splitlines():
        interface, address = line.split(": ", 1)
        assert interface
        assert address
        assert "/" in address


def test_mcp_registers_only_allowlisted_tools():
    tools = asyncio.run(mcp.list_tools())
    actual_tool_names = {tool.name for tool in tools}

    assert actual_tool_names == EXPECTED_TOOL_NAMES
