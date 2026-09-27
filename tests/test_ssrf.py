import ipaddress

import pytest

from core.ssrf import is_safe_destination


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.1.1",
        "::1",
        "fc00::1",
        "fe80::1",
        "224.0.0.1",
    ],
)
def test_ssrf_policy_rejects_non_public_addresses(address):
    assert not is_safe_destination(ipaddress.ip_address(address))


@pytest.mark.parametrize(
    "address",
    [
        "8.8.8.8",
        "1.1.1.1",
    ],
)
def test_ssrf_policy_accepts_public_global_addresses(address):
    assert is_safe_destination(ipaddress.ip_address(address))


def test_ssrf_policy_rejects_multicast_even_when_global():
    address = ipaddress.ip_address("224.0.0.1")

    assert address.is_global
    assert address.is_multicast
    assert not is_safe_destination(address)


def test_ssrf_policy_rejects_ipv6_multicast():
    address = ipaddress.ip_address("ff02::1")

    assert address.is_multicast
    assert not is_safe_destination(address)


def test_resolver_rejects_hostname_with_any_unsafe_address(monkeypatch):
    from core.ssrf import resolve_safe_addresses

    async def fake_getaddrinfo(*args, **kwargs):
        return [
            (2, 1, 6, "", ("8.8.8.8", 443)),
            (2, 1, 6, "", ("127.0.0.1", 443)),
        ]

    monkeypatch.setattr("anyio.getaddrinfo", fake_getaddrinfo)

    import asyncio

    with pytest.raises(ValueError, match="unsafe destination"):
        asyncio.run(resolve_safe_addresses("example.test", 443))


def test_resolver_accepts_all_public_addresses(monkeypatch):
    from core.ssrf import resolve_safe_addresses

    async def fake_getaddrinfo(*args, **kwargs):
        return [
            (2, 1, 6, "", ("8.8.8.8", 443)),
            (2, 1, 6, "", ("1.1.1.1", 443)),
        ]

    monkeypatch.setattr("anyio.getaddrinfo", fake_getaddrinfo)

    import asyncio

    addresses = asyncio.run(resolve_safe_addresses("example.test", 443))

    assert addresses == [
        ipaddress.ip_address("8.8.8.8"),
        ipaddress.ip_address("1.1.1.1"),
    ]


def test_backend_rejects_unsafe_address_before_connecting(monkeypatch):
    import asyncio

    from core.ssrf import SSRFNetworkBackend

    calls = []

    async def fake_connect_tcp(self, host, port, **kwargs):
        calls.append((host, port))
        return "unexpected-stream"

    from httpcore2 import AnyIOBackend

    monkeypatch.setattr(
        AnyIOBackend,
        "connect_tcp",
        fake_connect_tcp,
    )

    async def fake_resolve(hostname, port):
        return [
            ipaddress.ip_address("8.8.8.8"),
            ipaddress.ip_address("127.0.0.1"),
        ]

    monkeypatch.setattr(
        "core.ssrf.resolve_safe_addresses",
        fake_resolve,
    )

    backend = SSRFNetworkBackend()

    with pytest.raises(ValueError, match="unsafe destination"):
        asyncio.run(
            backend.connect_tcp("example.test", 443)
        )

    assert calls == []


def test_backend_falls_back_to_next_validated_address(monkeypatch):
    import asyncio

    from core.ssrf import SSRFNetworkBackend

    calls = []

    async def fake_connect_tcp(self, host, port, **kwargs):
        calls.append((host, port))
        if host == "8.8.8.8":
            raise OSError("first address failed")
        return "second-stream"

    from httpcore2 import AnyIOBackend

    monkeypatch.setattr(
        AnyIOBackend,
        "connect_tcp",
        fake_connect_tcp,
    )

    async def fake_resolve(hostname, port):
        return [
            ipaddress.ip_address("8.8.8.8"),
            ipaddress.ip_address("1.1.1.1"),
        ]

    monkeypatch.setattr(
        "core.ssrf.resolve_safe_addresses",
        fake_resolve,
    )

    backend = SSRFNetworkBackend()

    result = asyncio.run(
        backend.connect_tcp("example.test", 443)
    )

    assert result == "second-stream"
    assert calls == [
        ("8.8.8.8", 443),
        ("1.1.1.1", 443),
    ]


def test_backend_never_connects_to_original_hostname(monkeypatch):
    import asyncio

    from core.ssrf import SSRFNetworkBackend

    calls = []

    async def fake_connect_tcp(self, host, port, **kwargs):
        calls.append((host, port))
        return "stream"

    from httpcore2 import AnyIOBackend

    monkeypatch.setattr(
        AnyIOBackend,
        "connect_tcp",
        fake_connect_tcp,
    )

    async def fake_resolve(hostname, port):
        return [
            ipaddress.ip_address("8.8.8.8"),
            ipaddress.ip_address("1.1.1.1"),
        ]

    monkeypatch.setattr(
        "core.ssrf.resolve_safe_addresses",
        fake_resolve,
    )

    backend = SSRFNetworkBackend()

    result = asyncio.run(
        backend.connect_tcp("example.test", 443)
    )

    assert result == "stream"
    assert calls == [("8.8.8.8", 443)]
    assert all(host != "example.test" for host, _ in calls)


def test_ssrf_transport_security_configuration():
    import asyncio

    import httpx2

    from core.ssrf import SSRFAsyncHTTPTransport, SSRFNetworkBackend

    async def run():
        transport = SSRFAsyncHTTPTransport(
            verify=True,
            http1=True,
            http2=False,
            timeout=7.0,
        )

        client = httpx2.AsyncClient(
            transport=transport,
            verify=True,
            follow_redirects=False,
            trust_env=False,
            timeout=7.0,
        )

        assert isinstance(
            client._transport,
            httpx2.AsyncBaseTransport,
        )
        assert client._transport._pool._proxy is None
        assert client._transport._pool._retries == 0
        assert isinstance(
            client._transport._pool._network_backend,
            SSRFNetworkBackend,
        )
        assert client.follow_redirects is False
        assert client._trust_env is False
        assert client.timeout.connect == 7.0
        assert client._transport._timeout == 7.0

        await client.aclose()

    asyncio.run(run())


def test_ssrf_transport_preserves_original_hostname_for_tls_sni():
    import asyncio
    import ssl

    import httpcore2

    from core.ssrf import SSRFNetworkBackend

    class RecordingStream:
        def __init__(self):
            self.start_tls_calls = []

        def get_extra_info(self, info):
            return None

        async def start_tls(
            self,
            ssl_context,
            server_hostname=None,
            timeout=None,
        ):
            self.start_tls_calls.append(
                {
                    "server_hostname": server_hostname,
                    "timeout": timeout,
                    "ssl_context_type": type(ssl_context).__name__,
                }
            )
            raise RuntimeError("CONTROLLED_TLS_STOP")

    class RecordingBackend(SSRFNetworkBackend):
        def __init__(self):
            self.connect_calls = []
            self.stream = RecordingStream()

        async def connect_tcp(
            self,
            host,
            port,
            timeout=None,
            local_address=None,
            socket_options=None,
        ):
            self.connect_calls.append(
                {
                    "host": host,
                    "port": port,
                    "timeout": timeout,
                }
            )
            return self.stream

    async def run():
        backend = RecordingBackend()

        connection = httpcore2.AsyncHTTPConnection(
            origin=httpcore2.Origin(
                scheme=b"https",
                host=b"example.com",
                port=443,
            ),
            ssl_context=ssl.create_default_context(),
            network_backend=backend,
            retries=0,
        )

        request = httpcore2.Request(
            method=b"GET",
            url=httpcore2.URL(
                scheme=b"https",
                host=b"example.com",
                port=443,
                target=b"/",
            ),
            headers=[],
            content=b"",
            extensions={
                "timeout": {
                    "connect": 5.0,
                }
            },
        )

        with pytest.raises(
            RuntimeError,
            match="CONTROLLED_TLS_STOP",
        ):
            await connection._connect(request)

        assert backend.connect_calls == [
            {
                "host": "example.com",
                "port": 443,
                "timeout": 5.0,
            }
        ]

        assert backend.stream.start_tls_calls == [
            {
                "server_hostname": "example.com",
                "timeout": 5.0,
                "ssl_context_type": "SSLContext",
            }
        ]

    asyncio.run(run())


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/",
        "ftp://example.com/",
        "file:///etc/passwd",
        "gopher://example.com/",
    ],
)
def test_validate_ssrf_url_rejects_non_https(url):
    from core.ssrf import validate_ssrf_url

    with pytest.raises(ValueError, match="HTTPS"):
        validate_ssrf_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://user@example.com/",
        "https://user:password@example.com/",
    ],
)
def test_validate_ssrf_url_rejects_url_credentials(url):
    from core.ssrf import validate_ssrf_url

    with pytest.raises(ValueError, match="credentials"):
        validate_ssrf_url(url)


def test_validate_ssrf_url_accepts_basic_https_url():
    from core.ssrf import validate_ssrf_url

    result = validate_ssrf_url("https://example.com/path")

    assert result.scheme == "https"
    assert result.host == "example.com"
    assert result.path == "/path"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com:80/",
        "https://example.com:22/",
        "https://example.com:8080/",
        "https://example.com:8443/",
    ],
)
def test_validate_ssrf_url_rejects_disallowed_ports(url):
    from core.ssrf import validate_ssrf_url

    with pytest.raises(ValueError, match="port"):
        validate_ssrf_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/",
        "https://example.com:443/",
    ],
)
def test_validate_ssrf_url_accepts_https_port_443(url):
    from core.ssrf import validate_ssrf_url

    result = validate_ssrf_url(url)

    assert result.scheme == "https"
    assert result.host == "example.com"
    assert result.port in (None, 443)


def test_create_ssrf_client_disables_redirects_and_environment():
    import asyncio

    import httpx2

    from core.ssrf import create_ssrf_client

    async def run():
        client = create_ssrf_client()

        assert isinstance(client, httpx2.AsyncClient)
        assert client.follow_redirects is False
        assert client._trust_env is False
        assert client._transport._pool._proxy is None

        await client.aclose()

    asyncio.run(run())

def test_transport_rejects_invalid_request_url():
    import asyncio

    import httpx2
    import pytest

    from core.ssrf import SSRFAsyncHTTPTransport

    transport = SSRFAsyncHTTPTransport()

    request = httpx2.Request("GET",
        "http://example.com/",
    )

    async def run():
        return await transport.handle_async_request(request)

    with pytest.raises(ValueError, match="HTTPS URLs are required"):
        asyncio.run(run())

def test_transport_rejects_response_above_size_limit_from_content_length(monkeypatch):
    import asyncio

    import httpcore2
    import httpx2
    import pytest

    from core.ssrf import SSRFAsyncHTTPTransport

    transport = SSRFAsyncHTTPTransport()

    async def fake_handle_async_request(request):
        return httpcore2.Response(
            200,
            headers=[
                (b"content-length", b"1048577"),
            ],
            content=b"",
        )

    monkeypatch.setattr(
        transport._pool,
        "handle_async_request",
        fake_handle_async_request,
    )

    request = httpx2.Request(
        "GET",
        "https://example.com/",
    )

    async def run():
        return await transport.handle_async_request(request)

    with pytest.raises(ValueError, match="response exceeds maximum size"):
        asyncio.run(run())

def test_transport_rejects_stream_above_size_limit_without_content_length(monkeypatch):
    import asyncio

    import httpcore2
    import httpx2
    import pytest

    from core.ssrf import SSRFAsyncHTTPTransport

    class FakeStream:
        def __init__(self):
            self.closed = False

        def __aiter__(self):
            return self._iterate()

        async def _iterate(self):
            yield b"x" * 1048576
            yield b"y"

        async def aclose(self):
            self.closed = True

    stream = FakeStream()
    transport = SSRFAsyncHTTPTransport()

    async def fake_handle_async_request(request):
        return httpcore2.Response(
            200,
            headers=[],
            content=stream,
        )

    monkeypatch.setattr(
        transport._pool,
        "handle_async_request",
        fake_handle_async_request,
    )

    request = httpx2.Request(
        "GET",
        "https://example.com/",
    )

    async def run():
        response = await transport.handle_async_request(request)
        async for _ in response.aiter_bytes():
            pass

    with pytest.raises(ValueError, match="response exceeds maximum size"):
        asyncio.run(run())

    assert stream.closed is True

def test_transport_rejects_negative_content_length(monkeypatch):
    import asyncio

    import httpcore2
    import httpx2
    import pytest

    from core.ssrf import SSRFAsyncHTTPTransport

    transport = SSRFAsyncHTTPTransport()

    async def fake_handle_async_request(request):
        return httpcore2.Response(
            200,
            headers=[
                (b"content-length", b"-1"),
            ],
            content=b"",
        )

    monkeypatch.setattr(
        transport._pool,
        "handle_async_request",
        fake_handle_async_request,
    )

    request = httpx2.Request(
        "GET",
        "https://example.com/",
    )

    async def run():
        return await transport.handle_async_request(request)

    with pytest.raises(ValueError, match="invalid Content-Length header"):
        asyncio.run(run())

def test_transport_closes_response_for_invalid_content_length(monkeypatch):
    import asyncio

    import httpcore2
    import httpx2
    import pytest

    from core.ssrf import SSRFAsyncHTTPTransport

    transport = SSRFAsyncHTTPTransport()
    closed = False

    async def fake_aclose():
        nonlocal closed
        closed = True

    async def fake_handle_async_request(request):
        response = httpcore2.Response(
            200,
            headers=[
                (b"content-length", b"-1"),
            ],
            content=b"",
        )
        response.aclose = fake_aclose
        return response

    monkeypatch.setattr(
        transport._pool,
        "handle_async_request",
        fake_handle_async_request,
    )

    request = httpx2.Request(
        "GET",
        "https://example.com/",
    )

    async def run():
        return await transport.handle_async_request(request)

    with pytest.raises(ValueError, match="invalid Content-Length header"):
        asyncio.run(run())

    assert closed is True

def test_transport_rejects_conflicting_content_lengths(monkeypatch):
    import asyncio

    import httpcore2
    import httpx2
    import pytest

    from core.ssrf import SSRFAsyncHTTPTransport

    transport = SSRFAsyncHTTPTransport()

    async def fake_handle_async_request(request):
        return httpcore2.Response(
            200,
            headers=[
                (b"content-length", b"100"),
                (b"content-length", b"200"),
            ],
            content=b"",
        )

    monkeypatch.setattr(
        transport._pool,
        "handle_async_request",
        fake_handle_async_request,
    )

    request = httpx2.Request(
        "GET",
        "https://example.com/",
    )

    async def run():
        return await transport.handle_async_request(request)

    with pytest.raises(ValueError, match="conflicting Content-Length headers"):
        asyncio.run(run())

def test_transport_blocks_redirect_to_non_https(monkeypatch):
    import asyncio

    import httpcore2
    import httpx2
    import pytest

    from core.ssrf import SSRFAsyncHTTPTransport

    transport = SSRFAsyncHTTPTransport()
    calls = 0

    async def fake_handle_async_request(request):
        nonlocal calls
        calls += 1

        return httpcore2.Response(
            302,
            headers=[
                (b"location", b"http://example.com/"),
            ],
            content=b"",
        )

    monkeypatch.setattr(
        transport._pool,
        "handle_async_request",
        fake_handle_async_request,
    )

    async def run():
        async with httpx2.AsyncClient(
            transport=transport,
            follow_redirects=True,
            trust_env=False,
        ) as client:
            return await client.get("https://example.com/")

    with pytest.raises(ValueError, match="HTTPS URLs are required"):
        asyncio.run(run())

    assert calls == 1


