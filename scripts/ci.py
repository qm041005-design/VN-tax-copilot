"""Run the integrated suite and HTTP smoke on a disposable PostgreSQL database."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

import pytesseract
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
TOKEN = "ci-smoke-token-0001"


def prepare_environment() -> dict[str, str]:
    database = os.environ.get("TEST_DATABASE_URL", "")
    if not database:
        raise RuntimeError("Set TEST_DATABASE_URL to the disposable vntax_test database.")
    url = make_url(database)
    if url.get_backend_name() != "postgresql" or url.database != "vntax_test":
        raise RuntimeError("Refusing destructive tests: use PostgreSQL database vntax_test only.")
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            version = connection.execute(text("SHOW server_version_num")).scalar_one()
            if int(version) // 10000 != 16:
                raise RuntimeError("The integrated CI baseline requires PostgreSQL 16.")
            print(f"PostgreSQL ready (server_version_num={version}).", flush=True)
    finally:
        engine.dispose()
    if "vie" not in pytesseract.get_languages(config=""):
        raise RuntimeError("Install tesseract-ocr-vie; OCR tests must not silently skip.")
    if not Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf").is_file():
        raise RuntimeError("Install fonts-dejavu-core or run compose.test.yml on Docker Linux.")
    return {
        **os.environ,
        "DATABASE_URL": database,
        "TEST_DATABASE_URL": database,
        "PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT / "backend"))),
        "AUTH_TOKENS": f"{TOKEN}:ci:thtax",
        "SMOKE_API_TOKEN": TOKEN,
        "APP_ENV": "dev",
        "CORS_ORIGINS": "http://localhost:3000",
    }


def run_smoke(env: dict[str, str]) -> None:
    log_path = ARTIFACTS / "api.log"
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"
    with log_path.open("w", encoding="utf-8") as log:
        api = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", "backend",
             "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(60):
                if api.poll() is not None:
                    raise RuntimeError("API exited before becoming healthy; see artifacts/api.log.")
                try:
                    with urlopen(f"{base_url}/health", timeout=2) as response:
                        health = json.load(response)
                    if health.get("status") == "ok" and health.get("database") is True:
                        break
                except (URLError, TimeoutError, ValueError):
                    pass
                time.sleep(1)
            else:
                raise RuntimeError("API readiness timed out; see artifacts/api.log.")
            result = subprocess.run(
                [sys.executable, "backend/scripts/smoke_public_source.py",
                 "--confirm-test-database", "vntax_test", "--base-url", base_url],
                cwd=ROOT, env=env, text=True, capture_output=True,
            )
            (ARTIFACTS / "smoke.log").write_text(result.stdout + result.stderr, encoding="utf-8")
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            result.check_returncode()
        finally:
            api.terminate()
            try:
                api.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api.kill()
                api.wait()


def main() -> None:
    ARTIFACTS.mkdir(exist_ok=True)
    env = prepare_environment()
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-ra", "--junitxml=artifacts/pytest.xml"],
        cwd=ROOT, env=env, check=True,
    )
    run_smoke(env)


if __name__ == "__main__":
    main()
