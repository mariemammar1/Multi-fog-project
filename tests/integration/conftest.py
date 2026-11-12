
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FOGS = {
    "fog-a": "university",
    "fog-b": "shopping_center",
    "fog-c": "public_parking",
}


def get_free_port():
    """Find an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_fog(fog_id, url, process, timeout=30):
    """Wait until a Fog responds successfully to its health endpoint."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"{fog_id} stopped unexpectedly with code {process.returncode}."
            )

        try:
            response = httpx.get(f"{url}/health", timeout=1.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass

        time.sleep(0.25)

    raise RuntimeError(f"{fog_id} did not become healthy within {timeout} seconds.")


@pytest.fixture(scope="function")
def fog_cluster(tmp_path_factory):
    """
    Start three independent Fog processes with separate SQLite databases.
    Stop all processes when the integration test session ends.
    """
    ports = {fog_id: get_free_port() for fog_id in FOGS}
    urls = {
        fog_id: f"http://127.0.0.1:{port}"
        for fog_id, port in ports.items()
    }

    test_dir = tmp_path_factory.mktemp("multi_fog")
    db_dir = test_dir / "databases"
    log_dir = test_dir / "logs"

    db_dir.mkdir()
    log_dir.mkdir()

    processes = []

    try:
        for fog_id, zone in FOGS.items():
            env = os.environ.copy()

            env["FOG_ID"] = fog_id
            env["FOG_ZONE"] = zone
            env["FOG_DB_PATH"] = str(db_dir / f"{fog_id}.db")

            env["FOG_A_URL"] = urls["fog-a"]
            env["FOG_B_URL"] = urls["fog-b"]
            env["FOG_C_URL"] = urls["fog-c"]

            env["PYTHONPATH"] = (
                str(PROJECT_ROOT)
                + os.pathsep
                + env.get("PYTHONPATH", "")
            )
            env["PYTHONUNBUFFERED"] = "1"

            log_path = log_dir / f"{fog_id}.log"

            with open(log_path, "w", encoding="utf-8") as log_file:
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "fog.api.main:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(ports[fog_id]),
                    ],
                    cwd=PROJECT_ROOT,
                    env=env,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                )

            processes.append((fog_id, process))

            try:
                wait_for_fog(fog_id, urls[fog_id], process)
            except RuntimeError as error:
                log_content = log_path.read_text(encoding="utf-8")
                raise RuntimeError(
                    f"{error}\n\nLog of {fog_id}:\n{log_content}"
                ) from error

        urls["_processes"] = {
            fog_id: process
            for fog_id, process in processes
        }

        yield urls

    finally:
        for fog_id, process in reversed(processes):
            if process.poll() is None:
                process.terminate()

            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
