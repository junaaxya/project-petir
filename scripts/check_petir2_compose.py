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
        "--profile",
        "cloudflare-access",
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
jwks_proxy = services["jwks-egress-proxy"]

assert set(web["networks"]) == {"internal", "host_ingress"}, web["networks"]
assert set(server["networks"]) == {"internal", "jwks_client"}, server["networks"]
assert set(postgres["networks"]) == {"internal"}, postgres["networks"]
assert set(jwks_proxy["networks"]) == {"jwks_client", "jwks_egress"}, jwks_proxy["networks"]
assert networks["internal"]["internal"] is True
assert networks["jwks_client"]["internal"] is True
assert not networks["host_ingress"].get("internal", False)
assert not networks["jwks_egress"].get("internal", False)

assert not server.get("ports"), server.get("ports")
assert not postgres.get("ports"), postgres.get("ports")
assert not jwks_proxy.get("ports"), jwks_proxy.get("ports")
assert jwks_proxy.get("profiles") == ["cloudflare-access"]
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
assert environment["PETIR_RAIN_SEMANTICS"] == "rolling_1m_max"

server_environment = server["environment"]
assert server_environment["ADMIN_AUTH_MODE"] == "disabled"
assert server_environment["API_DOCS_ENABLED"] == "false"
assert server_environment["SIREN_AUDIT_ENABLED"] == "false"
assert server_environment["SIREN_AUDIT_OPERATORS_JSON"] == "[]"
assert server_environment["CLOUDFLARE_JWKS_PROXY_URL"] == "http://jwks-egress-proxy:3128"
assert server_environment["HEALTH_RESPONSE_MODE"] == "public_safe"
assert server_environment["PUBLIC_DATA_MODE"] == "public_safe"
assert jwks_proxy["environment"]["ALLOWED_JWKS_HOST"] == ""
assert "/healthz" in server["healthcheck"]["test"][-1]

print("Petir 2 Compose isolation, branding, rainfall semantics, and access-control contract: OK")
