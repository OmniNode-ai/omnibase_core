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
    host, _, port_str = raw.partition(":")
    return host, int(port_str) if port_str else 19092


class CheckKafka(DoctorCheckBase):
    check_id = "kafka"
    check_name = "Kafka/Redpanda"
    category = EnumDoctorCategory.SERVICES

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        host, port = _parse_kafka_bootstrap()
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
