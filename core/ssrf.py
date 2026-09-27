from __future__ import annotations

import ipaddress
import socket
import ssl
from collections.abc import Iterable

import httpcore2
import httpx2
from httpx2._transports.default import AsyncResponseStream, map_httpcore_exceptions


IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
MAX_RESPONSE_SIZE = 1024 * 1024


def validate_ssrf_url(url: str) -> httpx2.URL:
    """Validate the URL scheme and reject embedded credentials."""
    parsed = httpx2.URL(url)

    if parsed.scheme != "https":
        raise ValueError("HTTPS URLs are required")

    if parsed.username or parsed.password:
        raise ValueError("URL credentials are not allowed")

    if not parsed.host:
        raise ValueError("URL hostname is required")

    if parsed.port not in (None, 443):
        raise ValueError("port is not allowed")

    return parsed


def is_safe_destination(ip: IPAddress) -> bool:
    """Return True only for globally routable unicast IP addresses."""
    return (
        ip.is_global
        and not ip.is_loopback
        and not ip.is_private
        and not ip.is_link_local
        and not ip.is_multicast
        and not ip.is_reserved
    )


async def resolve_safe_addresses(hostname: str, port: int) -> list[IPAddress]:
    """Resolve a hostname and reject it if any resolved address is unsafe."""
    import anyio

    results = await anyio.getaddrinfo(
        hostname,
        port,
        type=socket.SOCK_STREAM,
    )

    addresses: list[IPAddress] = []
    seen: set[IPAddress] = set()

    for _, _, _, _, sockaddr in results:
        address = ipaddress.ip_address(sockaddr[0])

        if not is_safe_destination(address):
            raise ValueError(f"unsafe destination: {address}")

        if address not in seen:
            seen.add(address)
            addresses.append(address)

    if not addresses:
        raise ValueError("hostname did not resolve to any address")

    return addresses


class SizeLimitedAsyncByteStream(httpx2.AsyncByteStream):
    """Async response stream that enforces a maximum byte count."""

    def __init__(
        self,
        stream: httpx2.AsyncByteStream,
        *,
        max_bytes: int,
    ) -> None:
        self._stream = stream
        self._max_bytes = max_bytes
        self._bytes_read = 0

    async def __aiter__(self):
        async for chunk in self._stream:
            self._bytes_read += len(chunk)

            if self._bytes_read > self._max_bytes:
                await self.aclose()
                raise ValueError("response exceeds maximum size")

            yield chunk

    async def aclose(self) -> None:
        await self._stream.aclose()


class SSRFAsyncHTTPTransport(httpx2.AsyncBaseTransport):
    """httpx2 transport backed by the SSRF-validated network backend."""

    def __init__(
        self,
        *,
        verify=True,
        http1: bool = True,
        http2: bool = False,
        max_connections: int | None = 100,
        max_keepalive_connections: int | None = 20,
        keepalive_expiry: float | None = 5.0,
        timeout: float | None = 5.0,
    ) -> None:
        if verify is True:
            ssl_context = ssl.create_default_context()
        elif verify is False:
            raise ValueError("TLS verification must remain enabled")
        elif isinstance(verify, ssl.SSLContext):
            ssl_context = verify
        else:
            raise TypeError("verify must be True or an ssl.SSLContext")

        self._pool = httpcore2.AsyncConnectionPool(
            ssl_context=ssl_context,
            proxy=None,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            http1=http1,
            http2=http2,
            retries=0,
            network_backend=SSRFNetworkBackend(),
        )

        self._timeout = timeout

    async def handle_async_request(
        self,
        request: httpx2.Request,
    ) -> httpx2.Response:
        assert request.stream is not None
        validate_ssrf_url(str(request.url))

        req = httpcore2.Request(
            method=request.method,
            url=httpcore2.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )

        if self._timeout is not None:
            timeout_extensions = dict(req.extensions.get("timeout", {}))
            timeout_extensions.setdefault("connect", self._timeout)
            timeout_extensions.setdefault("read", self._timeout)
            timeout_extensions.setdefault("write", self._timeout)
            timeout_extensions.setdefault("pool", self._timeout)
            req.extensions["timeout"] = timeout_extensions

        with map_httpcore_exceptions():
            resp = await self._pool.handle_async_request(req)

        content_lengths = [
            value
            for name, value in resp.headers
            if name.lower() == b"content-length"
        ]

        if len(set(content_lengths)) > 1:
            await resp.aclose()
            raise ValueError("conflicting Content-Length headers")

        if content_lengths:
            try:
                response_size = int(content_lengths[0])
            except ValueError as exc:
                await resp.aclose()
                raise ValueError("invalid Content-Length header") from exc

            if response_size < 0:
                await resp.aclose()
                raise ValueError("invalid Content-Length header")

            if response_size > MAX_RESPONSE_SIZE:
                await resp.aclose()
                raise ValueError("response exceeds maximum size")

        response_stream = SizeLimitedAsyncByteStream(
            AsyncResponseStream(resp.stream),
            max_bytes=MAX_RESPONSE_SIZE,
        )

        return httpx2.Response(
            status_code=resp.status,
            headers=resp.headers,
            stream=response_stream,
            extensions=resp.extensions,
        )

    async def aclose(self) -> None:
        await self._pool.aclose()

    async def __aenter__(self) -> "SSRFAsyncHTTPTransport":
        await self._pool.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self._pool.__aexit__(exc_type, exc_value, traceback)


def create_ssrf_client(
    *,
    timeout: float = 5.0,
) -> httpx2.AsyncClient:
    """Create an HTTP client with the SSRF security boundary enabled."""
    transport = SSRFAsyncHTTPTransport(
        verify=True,
        timeout=timeout,
    )

    return httpx2.AsyncClient(
        transport=transport,
        follow_redirects=False,
        trust_env=False,
        timeout=timeout,
    )


class SSRFNetworkBackend:
    """Network backend that connects only to DNS-validated public IPs."""

    def __init__(self) -> None:
        from httpcore2 import AnyIOBackend

        self._backend = AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[object] | None = None,
    ) -> httpcore2.AsyncNetworkStream:
        addresses = await resolve_safe_addresses(host, port)

        for address in addresses:
            if not is_safe_destination(address):
                raise ValueError(f"unsafe destination: {address}")

        last_error = None

        for address in addresses:
            try:
                return await self._backend.connect_tcp(
                    str(address),
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except Exception as exc:
                last_error = exc

        if last_error is not None:
            raise last_error

        raise ValueError("no safe destination available")
