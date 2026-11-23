"""Run the isolated Identity, Events and Purchases Compose verification."""

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "verify_identity_integration.py"),
        run_name="__main__",
    )
