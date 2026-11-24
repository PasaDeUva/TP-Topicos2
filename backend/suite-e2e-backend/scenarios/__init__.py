"""Registro de escenarios multiservicio (orquestación entre servicios)."""

from collections.abc import Callable

from . import (
    test_compra_exitosa,
    test_compra_fallida,
    test_resilience_and_logs,
    test_rollback,
    test_session_lifecycle,
)

SCENARIOS: list[tuple[str, Callable]] = [
    ("test_compra_exitosa", test_compra_exitosa.run),
    ("test_compra_fallida", test_compra_fallida.run),
    ("test_session_lifecycle", test_session_lifecycle.run),
    ("test_resilience_and_logs", test_resilience_and_logs.run),
    ("test_rollback", test_rollback.run),
]

__all__ = ["SCENARIOS"]
