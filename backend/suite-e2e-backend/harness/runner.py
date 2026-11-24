"""Runner compartido para escenarios sobre un entorno Compose aislado.

Lo usan tanto los `verify_compose.py` de cada servicio (escenarios aislados)
como `run_e2e.py` (escenarios multiservicio).
"""

import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path

from .context import E2EContext
from .environment import setup_environment

SOURCE_ROOT = Path(__file__).resolve().parents[3]

Scenario = tuple[str, Callable[[E2EContext], None]]


def run_scenarios(
    title: str,
    scenarios: list[Scenario],
    rollback_ref: str | None = None,
) -> int:
    """Levanta el entorno, ejecuta los escenarios en orden y devuelve exit code."""
    total = len(scenarios)
    print(f"\n=== {title} ({total} scenarios) ===\n")
    start_total = time.monotonic()
    passed = 0

    try:
        with setup_environment(SOURCE_ROOT, rollback_ref=rollback_ref) as ctx:
            for idx, (name, scenario_fn) in enumerate(scenarios, start=1):
                print(f"[{idx}/{total}] Running {name}...", end=" ", flush=True)
                start = time.monotonic()
                try:
                    scenario_fn(ctx)
                except Exception as exc:
                    print(f"FAILED ({time.monotonic() - start:.2f}s)")
                    print(f"\nScenario '{name}' failed: {exc}\n", file=sys.stderr)
                    traceback.print_exc()
                    return 1
                print(f"PASSED ({time.monotonic() - start:.2f}s)")
                passed += 1
    except Exception as exc:
        print(f"\nFatal error during environment execution: {exc}\n", file=sys.stderr)
        traceback.print_exc()
        return 1

    elapsed = time.monotonic() - start_total
    print(f"\n=== {passed}/{total} scenarios PASSED in {elapsed:.2f}s ===\n")
    return 0
