"""Security and log auditing utilities for E2E tests."""

import re


def assert_no_secrets_in_logs(logs: str, secrets: list[str]):
    """Verify that no sensitive secrets or credentials leaked into container logs."""
    for secret in secrets:
        if secret:
            assert secret not in logs, f"Secret leaked in container logs: {secret[:4]}..."


def redact_logs(logs: str, secrets: list[str]) -> str:
    """Redact sensitive secrets and JWT tokens from container logs for safe output."""
    redacted = logs
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[redacted]")
    # Redact standard JWT signatures and bodies
    redacted = re.sub(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[redacted]", redacted)
    return redacted
