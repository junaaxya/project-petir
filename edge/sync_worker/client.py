from __future__ import annotations

import time
from typing import Any

import httpx

from petir_contracts import SyncBatchResponse

from sync_worker.config import Config


class RetriableError(Exception):
    pass


class FatalBatchError(Exception):
    def __init__(self, status_code: int, body: str) -> None:
        super().__init__(f"fatal batch error {status_code}: {body}")
        self.status_code = status_code
        self.body = body


class BackpressureError(Exception):
    pass


class SyncClient:
    def __init__(self, config: Config, client: httpx.Client | None = None) -> None:
        self._config = config
        self._client = client or httpx.Client(timeout=config.request_timeout_s)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._config.node_token}"}

    def post_batch(self, envelope: dict[str, Any]) -> SyncBatchResponse:
        attempt = 0
        while True:
            attempt += 1
            try:
                resp = self._client.post(
                    self._config.sync_batch_url,
                    json=envelope,
                    headers=self._headers(),
                )
            except httpx.TransportError as exc:
                if attempt > self._config.max_retries:
                    raise RetriableError(str(exc)) from exc
                self._sleep(attempt)
                continue

            if resp.status_code == 200:
                return SyncBatchResponse.model_validate(resp.json())
            if resp.status_code == 429:
                raise BackpressureError("server requested backpressure (429)")
            if 500 <= resp.status_code < 600:
                if attempt > self._config.max_retries:
                    raise RetriableError(f"server {resp.status_code}")
                self._sleep(attempt)
                continue
            raise FatalBatchError(resp.status_code, resp.text)

    def _sleep(self, attempt: int) -> None:
        delay = min(
            self._config.backoff_base_s * (2 ** (attempt - 1)),
            self._config.backoff_cap_s,
        )
        time.sleep(delay)

    def close(self) -> None:
        self._client.close()
