"""BAD: This handler imports from fake_infra.services which is forbidden."""

from __future__ import annotations

from fake_infra.services.service_kafka import ServiceKafka  # VIOLATION


class BadHandler:
    """Handler that violates import rules."""

    def __init__(self) -> None:
        self.kafka = ServiceKafka(None)  # type: ignore[arg-type]
