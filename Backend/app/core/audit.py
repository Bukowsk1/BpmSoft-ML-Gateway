from __future__ import annotations

import json
import logging
from typing import Any


audit_logger = logging.getLogger("app.audit")


def log_audit(event: str, request_id: str | None, **payload: Any) -> None:
    body = {"event": event, "request_id": request_id, **payload}
    audit_logger.info(json.dumps(body, ensure_ascii=False, default=str))
