import pytest

from app.web_config import load_web_session_config


@pytest.fixture
def production_config(monkeypatch):
    monkeypatch.setenv("IDENTITY_ENV", "production")
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", "https://app.example.com")
    monkeypatch.setenv("IDENTITY_WEB_CSRF_SECRET", "a" * 32)
    monkeypatch.delenv("IDENTITY_WEB_ALLOW_LOCAL_HTTP", raising=False)


def test_production_config_uses_secure_host_only_cookie(production_config):
    config = load_web_session_config()
    assert config.allowed_origins == {"https://app.example.com"}
    assert config.cookie_secure is True
    assert config.cookie_path == "/auth/web"
    assert config.cookie_samesite == "strict"
    assert "a" * 32 not in repr(config)


@pytest.mark.parametrize("name", ["IDENTITY_WEB_ORIGINS", "IDENTITY_WEB_CSRF_SECRET"])
def test_missing_production_configuration_is_rejected(production_config, monkeypatch, name):
    monkeypatch.delenv(name)
    with pytest.raises(ValueError):
        load_web_session_config()


@pytest.mark.parametrize("origin", ["*", "null", "https://example.com/", "https://user@example.com", "https://example.com?x=1", "http://localhost:5174", "https://example.com:99999"])
def test_invalid_or_insecure_origins_are_rejected(production_config, monkeypatch, origin):
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", origin)
    with pytest.raises(ValueError):
        load_web_session_config()


def test_local_http_requires_explicit_local_configuration(production_config, monkeypatch):
    monkeypatch.setenv("IDENTITY_WEB_ALLOW_LOCAL_HTTP", "true")
    with pytest.raises(ValueError):
        load_web_session_config()
    monkeypatch.setenv("IDENTITY_ENV", "local")
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", "http://localhost:5174")
    assert load_web_session_config().cookie_secure is False
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", "http://example.com")
    with pytest.raises(ValueError):
        load_web_session_config()


def test_short_secret_is_rejected(production_config, monkeypatch):
    monkeypatch.setenv("IDENTITY_WEB_CSRF_SECRET", "short")
    with pytest.raises(ValueError):
        load_web_session_config()


@pytest.mark.parametrize("origins", ["https://app.example.com,https://app.example.com:8443", "https://app.example.com,https://other.example.com"])
def test_multiple_frontend_origins_are_rejected(production_config, monkeypatch, origins):
    monkeypatch.setenv("IDENTITY_WEB_ORIGINS", origins)
    with pytest.raises(ValueError, match="Exactly one"):
        load_web_session_config()
