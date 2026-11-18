import fcntl
import json
import os
import subprocess
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy.orm import Session

from app.admin import initialize_admin
from app.database import _engine


def prepare_keys() -> None:
    if os.environ.get("IDENTITY_ENV") != "local":
        for name in ("JWT_PRIVATE_KEY", "JWT_PUBLIC_KEY", "JWT_ISSUER", "JWT_AUDIENCE", "ADMIN_EMAIL", "ADMIN_PASSWORD", "SERVICE_CREDENTIALS_JSON"):
            if not os.environ.get(name):
                raise RuntimeError(f"{name} must be configured")
        return

    if not os.environ.get("SERVICE_CREDENTIALS_JSON"):
        os.environ["SERVICE_CREDENTIALS_JSON"] = json.dumps({
            "events": {"token": os.environ["EVENTS_SERVICE_TOKEN"], "roles_read": True},
            "purchases": {"token": os.environ["PURCHASES_SERVICE_TOKEN"], "roles_read": True},
        })

    private_dir = Path(os.environ["JWT_PRIVATE_DIR"])
    public_dir = Path(os.environ["JWT_PUBLIC_DIR"])
    private_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)
    private_path = private_dir / "private.pem"
    public_path = public_dir / "public.pem"
    with (private_dir / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not private_path.exists():
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            encoded = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
            descriptor = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as output:
                output.write(encoded)
        private = private_path.read_bytes()
        key = serialization.load_pem_private_key(private, password=None)
        public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        public_path.write_bytes(public)
        os.environ["JWT_PRIVATE_KEY"] = private.decode()
        os.environ["JWT_PUBLIC_KEY"] = public.decode()


def main() -> None:
    prepare_keys()
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    with Session(_engine()) as session:
        initialize_admin(session, os.environ["ADMIN_EMAIL"], os.environ["ADMIN_PASSWORD"])
        session.commit()
    command = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    if os.environ.get("IDENTITY_ENV") == "local" and os.environ.get("UVICORN_RELOAD") == "true":
        command.extend(["--reload", "--reload-dir", "/app/app"])
    os.execvp("uvicorn", command)


if __name__ == "__main__":
    main()
