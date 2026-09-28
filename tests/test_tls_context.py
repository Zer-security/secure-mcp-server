import ssl

from server import create_tls_context


def test_create_tls_context_requires_tls_1_2():
    default_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    context = create_tls_context(
        None,
        lambda: default_context,
    )

    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
