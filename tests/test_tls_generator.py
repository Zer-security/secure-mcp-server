
import os

import pytest

import scripts.generate_tls as tls


def test_generate_certificate_creates_tls_directory_with_restricted_permissions(
    monkeypatch,
    tmp_path,
):
    tls_dir = tmp_path / "tls"

    monkeypatch.setattr(tls, "TLS_DIR", tls_dir)
    monkeypatch.setattr(tls, "KEY_PATH", tls_dir / "mcp-server.key.tmp")
    monkeypatch.setattr(tls, "CERT_PATH", tls_dir / "mcp-server.crt.tmp")

    previous_umask = os.umask(0o002)
    try:
        tls.generate_certificate("203.0.113.10")
    finally:
        os.umask(previous_umask)

    assert tls_dir.stat().st_mode & 0o777 == 0o700

def test_promote_certificate_success(monkeypatch, tmp_path):
    tls_dir = tmp_path / "tls"
    tls_dir.mkdir()

    monkeypatch.setattr(tls, "TLS_DIR", tls_dir)
    monkeypatch.setattr(tls, "KEY_PATH", tls_dir / "mcp-server.key.tmp")
    monkeypatch.setattr(tls, "CERT_PATH", tls_dir / "mcp-server.crt.tmp")
    monkeypatch.setattr(tls, "ACTIVE_KEY_PATH", tls_dir / "mcp-server.key")
    monkeypatch.setattr(tls, "ACTIVE_CERT_PATH", tls_dir / "mcp-server.crt")

    tls.generate_certificate("203.0.113.10")

    tls.promote_certificate("203.0.113.10")

    assert tls.ACTIVE_KEY_PATH.is_file()
    assert tls.ACTIVE_CERT_PATH.is_file()
    assert not tls.KEY_PATH.exists()
    assert not tls.CERT_PATH.exists()


def test_promote_certificate_rejects_mismatched_key_and_certificate(
    monkeypatch,
    tmp_path,
):
    tls_dir = tmp_path / "tls"
    tls_dir.mkdir()

    monkeypatch.setattr(tls, "TLS_DIR", tls_dir)
    monkeypatch.setattr(tls, "KEY_PATH", tls_dir / "mcp-server.key.tmp")
    monkeypatch.setattr(tls, "CERT_PATH", tls_dir / "mcp-server.crt.tmp")
    monkeypatch.setattr(tls, "ACTIVE_KEY_PATH", tls_dir / "mcp-server.key")
    monkeypatch.setattr(tls, "ACTIVE_CERT_PATH", tls_dir / "mcp-server.crt")

    tls.generate_certificate("203.0.113.10")

    original_key = tls.KEY_PATH.read_bytes()

    other_dir = tmp_path / "other"
    other_dir.mkdir()

    monkeypatch.setattr(
        tls,
        "KEY_PATH",
        other_dir / "mcp-server.key.tmp",
    )

    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization

    other_key = ec.generate_private_key(ec.SECP256R1())
    tls.KEY_PATH.write_bytes(
        other_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    with pytest.raises(
        RuntimeError,
        match="Private key dan certificate staging tidak cocok",
    ):
        tls.promote_certificate("203.0.113.10")

    assert tls.CERT_PATH.is_file()
    assert tls.KEY_PATH.is_file()
    assert tls.KEY_PATH.read_bytes() != original_key


def test_promote_certificate_rolls_back_when_certificate_replace_fails(
    monkeypatch,
    tmp_path,
):
    tls_dir = tmp_path / "tls"
    tls_dir.mkdir()

    monkeypatch.setattr(tls, "TLS_DIR", tls_dir)
    monkeypatch.setattr(tls, "KEY_PATH", tls_dir / "mcp-server.key.tmp")
    monkeypatch.setattr(tls, "CERT_PATH", tls_dir / "mcp-server.crt.tmp")
    monkeypatch.setattr(tls, "ACTIVE_KEY_PATH", tls_dir / "mcp-server.key")
    monkeypatch.setattr(tls, "ACTIVE_CERT_PATH", tls_dir / "mcp-server.crt")

    tls.generate_certificate("203.0.113.10")

    original_key = tls.ACTIVE_KEY_PATH
    original_cert = tls.ACTIVE_CERT_PATH

    tls.ACTIVE_KEY_PATH.write_bytes(b"OLD-KEY")
    tls.ACTIVE_CERT_PATH.write_bytes(b"OLD-CERT")

    original_replace = tls.os.replace
    calls = 0

    def fail_on_certificate_replace(source, destination):
        nonlocal calls
        calls += 1

        if destination == tls.ACTIVE_CERT_PATH:
            raise OSError("simulated certificate replacement failure")

        return original_replace(source, destination)

    monkeypatch.setattr(tls.os, "replace", fail_on_certificate_replace)

    with pytest.raises(
        OSError,
        match="simulated certificate replacement failure",
    ):
        tls.promote_certificate("203.0.113.10")

    assert calls == 2
    assert original_key.read_bytes() == b"OLD-KEY"
    assert original_cert.read_bytes() == b"OLD-CERT"
