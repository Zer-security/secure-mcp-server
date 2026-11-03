import asyncio
from urllib.parse import parse_qs, urlparse

from mcp.client.auth import AuthorizationCodeResult


class OAuthCallbackServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self._server = None
        self._result: AuthorizationCodeResult | None = None
        self._error: Exception | None = None
        self._event = asyncio.Event()

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_connection,
            self.host,
            self.port,
        )

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def wait_for_result(self) -> AuthorizationCodeResult:
        await self._event.wait()

        if self._error is not None:
            raise self._error

        if self._result is None:
            raise RuntimeError("OAuth callback tidak menerima hasil.")

        return self._result

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            request_line = await reader.readline()
            request = request_line.decode("utf-8", errors="replace").strip()

            parts = request.split()
            if len(parts) < 2 or parts[0] != "GET":
                await self._respond(writer, 400, "Bad Request")
                return

            path = urlparse(parts[1])
            params = parse_qs(path.query)

            if "error" in params:
                error = params["error"][0]
                description = params.get("error_description", [""])[0]
                self._error = RuntimeError(
                    f"OAuth authorization gagal: {error}"
                    + (f" - {description}" if description else "")
                )
                await self._respond(writer, 400, "OAuth authorization gagal.")
            elif "code" not in params:
                self._error = RuntimeError(
                    "OAuth callback tidak berisi authorization code."
                )
                await self._respond(writer, 400, "Authorization code tidak ditemukan.")
            else:
                self._result = AuthorizationCodeResult(
                    code=params["code"][0],
                    state=params.get("state", [None])[0],
                    iss=params.get("iss", [None])[0],
                )
                await self._respond(writer, 200, "Authorization berhasil. Kamu bisa menutup halaman ini.")

        except Exception as exc:
            self._error = exc
            try:
                await self._respond(writer, 500, "OAuth callback error.")
            except Exception:
                pass
        finally:
            self._event.set()
            writer.close()
            await writer.wait_closed()

    async def _respond(
        self,
        writer: asyncio.StreamWriter,
        status: int,
        message: str,
    ) -> None:
        body = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>MCP OAuth</title></head>
<body>
<h1>{message}</h1>
</body>
</html>
""".encode("utf-8")

        response = (
            f"HTTP/1.1 {status} {'OK' if status == 200 else 'Bad Request'}\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("ascii") + body

        writer.write(response)
        await writer.drain()
