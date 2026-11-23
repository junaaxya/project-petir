from __future__ import annotations

import time
from typing import Any

import httpx

from petir_contracts import CONTRACT_VERSION, SyncBatchResponse

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
                parsed = SyncBatchResponse.model_validate(resp.json())
                self._validate_ack(envelope, parsed)
                return parsed
            if resp.status_code == 429:
                raise BackpressureError("server requested backpressure (429)")
            if 500 <= resp.status_code < 600:
                if attempt > self._config.max_retries:
                    raise RetriableError(f"server {resp.status_code}")
                self._sleep(attempt)
                continue
            raise FatalBatchError(resp.status_code, resp.text)

    @staticmethod
    def _validate_ack(
        envelope: dict[str, Any], response: SyncBatchResponse
    ) -> None:
        expected_run_id = str(envelope.get("run_id", ""))
        expected_table = str(envelope.get("table", ""))
        expected_strategy = str(envelope.get("cursor", {}).get("strategy", ""))
        server_major = response.server_contract_version.split(".", 1)[0]
        client_major = CONTRACT_VERSION.split(".", 1)[0]

        if str(response.run_id) != expected_run_id:
            raise FatalBatchError(200, "invalid ACK: run_id mismatch")
        if response.table.value != expected_table:
            raise FatalBatchError(200, "invalid ACK: table mismatch")
        if server_major != client_major:
            raise FatalBatchError(200, "invalid ACK: contract major mismatch")
        if response.accepted_cursor.strategy is None or (
            response.accepted_cursor.strategy.value != expected_strategy
        ):
            raise FatalBatchError(200, "invalid ACK: cursor strategy mismatch")

        cursor_field = (
            "last_edge_id" if expected_strategy == "append" else "last_change_seq"
        )
        sent_cursor = envelope.get("cursor", {}).get(cursor_field)
        accepted_cursor = getattr(response.accepted_cursor, cursor_field)
        if (
            sent_cursor is not None
            and accepted_cursor is not None
            and accepted_cursor < sent_cursor
        ):
            raise FatalBatchError(200, "invalid ACK: cursor regression")
        row_cursor_field = "edge_id" if expected_strategy == "append" else "change_seq"
        row_cursor_values: list[int] = []
        for row in envelope.get("rows", []):
            if not isinstance(row, dict):
                continue
            value = row.get(row_cursor_field)
            if isinstance(value, int) and not isinstance(value, bool):
                row_cursor_values.append(value)
        if (
            accepted_cursor is not None
            and row_cursor_values
            and accepted_cursor > max(row_cursor_values)
        ):
            raise FatalBatchError(200, "invalid ACK: cursor exceeds batch")
        row_count = len(envelope.get("rows", []))
        if response.accepted > row_count:
            raise FatalBatchError(200, "invalid ACK: accepted count exceeds batch")
        if any(item.index >= row_count for item in response.rejected):
            raise FatalBatchError(200, "invalid ACK: rejected index outside batch")
        rejected_indexes = {item.index for item in response.rejected}
        if len(rejected_indexes) != len(response.rejected):
            raise FatalBatchError(200, "invalid ACK: duplicate rejected index")
        if response.accepted + len(response.rejected) != row_count:
            raise FatalBatchError(200, "invalid ACK: row counts do not cover batch")

    def _sleep(self, attempt: int) -> None:
        delay = min(
            self._config.backoff_base_s * (2 ** (attempt - 1)),
            self._config.backoff_cap_s,
        )
        time.sleep(delay)

    def close(self) -> None:
        self._client.close()
