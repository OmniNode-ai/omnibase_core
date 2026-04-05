# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import os
import socket
import time

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult


def _parse_kafka_bootstrap() -> tuple[str, int]:
    raw = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092")
    first = raw.split(",")[0].strip()
    host, sep, port_str = first.rpartition(":")
    if not sep:
        return (
            first,
            19092,
        )  # fallback-ok: no port separator — use default Redpanda port
    try:
        return host, int(port_str)
    except ValueError:
        # error-ok: re-raising with better message at system boundary
        raise ValueError(
            f"KAFKA_BOOTSTRAP_SERVERS contains non-numeric port: {port_str!r}"
        )


class CheckKafka(DoctorCheckBase):
    check_id = "kafka"
    check_name = "Kafka/Redpanda"
    category = EnumDoctorCategory.SERVICES

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        try:
            host, port = _parse_kafka_bootstrap()
        except ValueError as exc:
            return ModelDoctorCheckResult(
                name=self.check_name,
                category=self.category,
                status=EnumHealthStatusValue.UNHEALTHY,
                message=str(exc),
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        try:
            conn = socket.create_connection((host, port), timeout=3)
            conn.close()
            ok = True
        except (TimeoutError, OSError):
            ok = False
        return ModelDoctorCheckResult(
            name=self.check_name,
            category=self.category,
            status=EnumHealthStatusValue.HEALTHY
            if ok
            else EnumHealthStatusValue.UNHEALTHY,
            message="Redpanda reachable" if ok else "Redpanda not reachable",
            duration_ms=int((time.monotonic() - start) * 1000),
        )
