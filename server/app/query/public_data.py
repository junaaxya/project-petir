from __future__ import annotations

import base64
import hashlib
from uuid import UUID


def opaque_event_id(kind: str, node_id: str, db_epoch: UUID | str, edge_id: int) -> str:
    material = f"petir-public-v1\0{kind}\0{node_id}\0{db_epoch}\0{edge_id}".encode()
    digest = hashlib.sha256(material).digest()[:18]
    encoded = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return f"evt_{encoded}"
