from mcp.server.transport_security import (
    TransportSecurityMiddleware,
    TransportSecuritySettings,
)


def make_middleware() -> TransportSecurityMiddleware:
    settings = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["192.168.1.7:8000"],
    )
    return TransportSecurityMiddleware(settings)


def test_allowed_host():
    middleware = make_middleware()

    assert middleware._validate_host("192.168.1.7:8000") is True


def test_loopback_host_is_rejected():
    middleware = make_middleware()

    assert middleware._validate_host("127.0.0.1:8000") is False


def test_missing_host_is_rejected():
    middleware = make_middleware()

    assert middleware._validate_host(None) is False
