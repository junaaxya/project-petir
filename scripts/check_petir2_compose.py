#!/usr/bin/env python3
"""Fail closed when the Petir 2 Compose isolation contract drifts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy" / "petir2-nelayan"

result = subprocess.run(
    [
        "docker",
        "compose",
        "--env-file",
        str(DEPLOY / ".env.example"),
        "-f",
        str(DEPLOY / "compose.yml"),
        "config",
        "--format",
        "json",
    ],
    check=True,
    capture_output=True,
    text=True,
)
config = json.loads(result.stdout)
services = config["services"]
networks = config["networks"]

web = services["web"]
server = services["server"]
postgres = services["postgres"]

assert set(web["networks"]) == {"internal", "host_ingress"}, web["networks"]
assert set(server["networks"]) == {"internal"}, server["networks"]
assert set(postgres["networks"]) == {"internal"}, postgres["networks"]
assert networks["internal"]["internal"] is True
assert not networks["host_ingress"].get("internal", False)

assert not server.get("ports"), server.get("ports")
assert not postgres.get("ports"), postgres.get("ports")
ports = web.get("ports", [])
assert len(ports) == 1, ports
port = ports[0]
assert port["host_ip"] == "127.0.0.1", port
assert int(port["published"]) == 3020, port
assert int(port["target"]) == 3000, port

environment = web["environment"]
assert environment["HOSTNAME"] == "0.0.0.0"
assert environment["PETIR_SITE_NAME"] == "Nelayan Sungailiat"
assert environment["PETIR_STATION_VERSION"] == "2.0"
assert environment["PETIR_SITE_ID"] == "nelayan-sungailiat"
assert environment["PETIR_PUBLIC_DOMAIN"] == "nelayan-sungailiat.petirlabs.com"

print("Petir 2 Compose isolation and branding contract: OK")
