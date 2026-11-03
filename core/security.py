def ensure_non_root() -> None:
    """Pastikan MCP server tidak berjalan dengan privilege administratif."""
    import sys

    if sys.platform == "win32":
        import ctypes

        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception as exc:
            raise PermissionError(
                "Tidak dapat memverifikasi status administrator di Windows."
            ) from exc

        if is_admin:
            raise PermissionError(
                "MCP server tidak boleh dijalankan sebagai Administrator."
            )
    else:
        import os

        if os.geteuid() == 0:
            raise PermissionError(
                "MCP server tidak boleh dijalankan sebagai root."
            )
