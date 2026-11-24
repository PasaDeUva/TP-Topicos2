"""Ejecutor de los escenarios MULTISERVICIO (Identity + Events + Compras)."""

import argparse
import sys
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from harness import run_scenarios  # noqa: E402
from scenarios import SCENARIOS  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        help="Nombre(s) de escenario a ejecutar, separados por coma",
    )
    parser.add_argument(
        "--rollback-ref",
        help="Revisión Git para verificar la compatibilidad de rollback",
    )
    args = parser.parse_args(argv)

    scenarios = SCENARIOS
    if args.scenario:
        requested = [name.strip() for name in args.scenario.split(",")]
        scenarios = [s for s in SCENARIOS if s[0] in requested]
        if not scenarios:
            available = [name for name, _ in SCENARIOS]
            print(
                f"Escenario(s) '{args.scenario}' no encontrado(s). "
                f"Disponibles: {available}",
                file=sys.stderr,
            )
            return 1

    return run_scenarios(
        "Multi-Service E2E Backend Suite",
        scenarios,
        rollback_ref=args.rollback_ref,
    )


if __name__ == "__main__":
    sys.exit(main())
