import ssl

from server import create_tls_context


TLS_CIPHERS = "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384"


def test_create_tls_context_requires_tls_1_2():
    default_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context = create_tls_context(None, lambda: default_context)

    assert context.minimum_version == ssl.TLSVersion.TLSv1_2


def test_tls_12_cipher_policy():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.set_ciphers(TLS_CIPHERS)

    tls_12_ciphers = {
        cipher["name"]
        for cipher in context.get_ciphers()
        if cipher["protocol"] == "TLSv1.2"
    }

    assert tls_12_ciphers == {
        "ECDHE-ECDSA-AES128-GCM-SHA256",
        "ECDHE-ECDSA-AES256-GCM-SHA384",
    }
