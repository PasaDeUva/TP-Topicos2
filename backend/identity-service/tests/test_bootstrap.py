import os

import pytest
from cryptography.hazmat.primitives import serialization

from app.bootstrap import prepare_keys


def test_local_keys_are_persisted_and_public_key_matches(tmp_path, monkeypatch):
    private_dir = tmp_path / "private"
    public_dir = tmp_path / "public"
    monkeypatch.setenv("IDENTITY_ENV", "local")
    monkeypatch.setenv("JWT_PRIVATE_DIR", str(private_dir))
    monkeypatch.setenv("JWT_PUBLIC_DIR", str(public_dir))
    monkeypatch.setenv("EVENTS_SERVICE_TOKEN", "events-test")
    monkeypatch.setenv("PURCHASES_SERVICE_TOKEN", "purchases-test")
    monkeypatch.setenv("JWT_PRIVATE_KEY", "placeholder")
    monkeypatch.setenv("JWT_PUBLIC_KEY", "placeholder")
    monkeypatch.delenv("SERVICE_CREDENTIALS_JSON", raising=False)
    prepare_keys()
    original_private = (private_dir / "private.pem").read_bytes()
    original_public = (public_dir / "public.pem").read_bytes()
    assert (private_dir / "private.pem").stat().st_mode & 0o777 == 0o600
    key = serialization.load_pem_private_key(original_private, password=None)
    assert key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo) == original_public
    prepare_keys()
    assert (private_dir / "private.pem").read_bytes() == original_private
    assert (public_dir / "public.pem").read_bytes() == original_public
    assert os.environ["JWT_PUBLIC_KEY"].encode() == original_public


def test_nonlocal_requires_explicit_values(monkeypatch):
    monkeypatch.setenv("IDENTITY_ENV", "production")
    monkeypatch.delenv("JWT_PRIVATE_KEY", raising=False)
    with pytest.raises(RuntimeError, match="JWT_PRIVATE_KEY"):
        prepare_keys()
