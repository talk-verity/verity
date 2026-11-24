"""Apply migrations to a new Neon database without saving credentials."""
import getpass
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit


def main():
    url = getpass.getpass("Paste the Neon DIRECT connection string (hidden): ").strip()
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    parsed = urlsplit(url)
    if parsed.scheme != "postgresql+psycopg" or not (parsed.hostname or "").endswith(".neon.tech"):
        sys.exit("Expected a Neon PostgreSQL connection string.")
    if "-pooler" in parsed.hostname:
        sys.exit("Turn off connection pooling in Neon and copy the direct connection string.")
    if "sslmode=require" not in parsed.query and "sslmode=verify-full" not in parsed.query:
        sys.exit("Copy the full connection string including its SSL parameters.")
    backend = Path(__file__).resolve().parents[1] / "backend"
    python = backend / ".venv" / "bin" / "python"
    if not python.exists():
        sys.exit("Set up backend/.venv first, as described in README.md.")
    result = subprocess.run([str(python), "-m", "alembic", "upgrade", "head"],
                            cwd=backend, env={**os.environ, "DATABASE_URL": url})
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
