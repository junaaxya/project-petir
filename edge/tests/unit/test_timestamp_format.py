from __future__ import annotations

import re
from datetime import datetime

from sync_worker.run import _now_iso

_ISO_MS_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def test_now_iso_is_valid_iso8601_ms_z():
    value = _now_iso()
    assert _ISO_MS_Z.match(value), value
    datetime.fromisoformat(value.replace("Z", "+00:00"))
