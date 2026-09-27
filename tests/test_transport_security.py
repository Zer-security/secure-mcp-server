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


def test_request_body_limit_rejects_oversized_content_length():
    import asyncio

    from mcp.server.transport_security import RequestBodyLimitMiddleware

    async def downstream(scope, receive, send):
        raise AssertionError("DOWNSTREAM_SHOULD_NOT_BE_CALLED")

    async def run():
        app = RequestBodyLimitMiddleware(downstream, max_body_size=10)
        sent = []

        async def receive():
            raise AssertionError("BODY_SHOULD_NOT_BE_READ")

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "headers": [(b"content-length", b"11")],
        }

        await app(scope, receive, send)
        return sent

    sent = asyncio.run(run())

    assert sent[0]["status"] == 413
    assert sent[1]["body"] == b"Request body too large"


def test_request_body_limit_rejects_oversized_streamed_body():
    import asyncio

    from mcp.server.transport_security import RequestBodyLimitMiddleware

    async def downstream(scope, receive, send):
        raise AssertionError("DOWNSTREAM_SHOULD_NOT_BE_CALLED")

    async def run():
        app = RequestBodyLimitMiddleware(downstream, max_body_size=10)

        messages = iter(
            [
                {
                    "type": "http.request",
                    "body": b"123456",
                    "more_body": True,
                },
                {
                    "type": "http.request",
                    "body": b"78901",
                    "more_body": False,
                },
            ]
        )

        async def receive():
            return next(messages)

        sent = []

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "headers": [],
        }

        await app(scope, receive, send)
        return sent

    sent = asyncio.run(run())

    assert sent[0]["status"] == 413
    assert sent[1]["body"] == b"Request body too large"
