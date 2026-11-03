import psutil


def system_status() -> str:
    """Menampilkan status dasar sistem."""
    import platform

    return (
        f"OS: {platform.system()} {platform.release()}\n"
        f"Hostname: {platform.node()}\n"
        f"Python: {platform.python_version()}"
    )


def disk_status() -> str:
    """Menampilkan penggunaan disk root."""
    import shutil

    total, used, free = shutil.disk_usage("/")
    gb = 1024**3

    return (
        f"Disk total: {total / gb:.1f} GB\n"
        f"Disk terpakai: {used / gb:.1f} GB\n"
        f"Disk bebas: {free / gb:.1f} GB"
    )


def memory_status() -> str:
    """Menampilkan penggunaan RAM (cross-platform via psutil)."""
    vm = psutil.virtual_memory()
    gb = 1024**3

    return (
        f"RAM total: {vm.total / gb:.1f} GB\n"
        f"RAM terpakai: {vm.used / gb:.1f} GB\n"
        f"RAM tersedia: {vm.available / gb:.1f} GB"
    )


def network_status() -> str:
    """Menampilkan informasi jaringan dasar."""
    import socket

    hostname = socket.gethostname()

    try:
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        local_ip = "Tidak tersedia"

    return f"Hostname: {hostname}\nIP lokal: {local_ip}"
