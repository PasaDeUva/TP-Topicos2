import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.identity_config import load_identity_config


@pytest.fixture
def identity_env(monkeypatch, tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    path = tmp_path / "identity-public.pem"
    path.write_bytes(public_key)
    values = {
        "IDENTITY_URL": "https://identity.example.test",
        "IDENTITY_PUBLIC_KEY_PATH": str(path),
        "IDENTITY_ISSUER": "issuer",
        "IDENTITY_AUDIENCE": "audience",
        "IDENTITY_SERVICE_TOKEN": "test-only-secret",
        "IDENTITY_TIMEOUT_SECONDS": "0.8",
        "APP_ENV": "production",
        "IDENTITY_ALLOW_LOCAL_HTTP": "false",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return values


def test_identity_config_requires_valid_values_and_hides_secret(
    identity_env, monkeypatch
):
    config = load_identity_config()
    assert config.service_id == "purchases"
    assert "test-only-secret" not in repr(config)
    for name in (
        "IDENTITY_URL", "IDENTITY_PUBLIC_KEY_PATH", "IDENTITY_ISSUER",
        "IDENTITY_AUDIENCE", "IDENTITY_SERVICE_TOKEN",
    ):
        monkeypatch.delenv(name)
        with pytest.raises(ValueError):
            load_identity_config()
        monkeypatch.setenv(name, identity_env[name])


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "invalid"])
def test_identity_config_rejects_invalid_timeout(identity_env, monkeypatch, value):
    monkeypatch.setenv("IDENTITY_TIMEOUT_SECONDS", value)
    with pytest.raises(ValueError):
        load_identity_config()


def test_http_requires_explicit_local_opt_in(identity_env, monkeypatch):
    monkeypatch.setenv("IDENTITY_URL", "http://identity-service:8000")
    with pytest.raises(ValueError):
        load_identity_config()
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("IDENTITY_ALLOW_LOCAL_HTTP", "true")
    assert load_identity_config().identity_url == "http://identity-service:8000"
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(ValueError):
        load_identity_config()


def test_config_rejects_external_http_even_with_local_opt_in(identity_env, monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("IDENTITY_ALLOW_LOCAL_HTTP", "true")
    monkeypatch.setenv("IDENTITY_URL", "http://external.example.test")
    with pytest.raises(ValueError):
        load_identity_config()


@pytest.mark.parametrize(
    "url",
    [
        "https://user:pass@identity.example.test",
        "https://identity.example.test/path",
        "ftp://identity.example.test",
        "https://identity.example.test?token=x",
    ],
)
def test_config_rejects_unsafe_urls(identity_env, monkeypatch, url):
    monkeypatch.setenv("IDENTITY_URL", url)
    with pytest.raises(ValueError):
        load_identity_config()


def test_config_rejects_invalid_key_without_leaking_secret(
    identity_env, monkeypatch, tmp_path
):
    path = tmp_path / "invalid.pem"
    path.write_text("not a key", encoding="utf-8")
    monkeypatch.setenv("IDENTITY_PUBLIC_KEY_PATH", str(path))
    with pytest.raises(ValueError, match="Identity configuration unavailable") as error:
        load_identity_config()
    assert "test-only-secret" not in str(error.value)


@pytest.mark.parametrize("token", [" ", "line\nbreak", "invalid\x7f", "ñ"])
def test_config_rejects_tokens_that_cannot_be_sent_as_headers(
    identity_env, monkeypatch, token
):
    monkeypatch.setenv("IDENTITY_SERVICE_TOKEN", token)
    with pytest.raises(ValueError):
        load_identity_config()
