# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import socket
import time

from omnibase_core.doctor.doctor_check_base import DoctorCheckBase
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue
from omnibase_core.models.doctor.model_doctor_check_result import ModelDoctorCheckResult
from omnibase_core.models.doctor.model_postgres_probe_config import (
    ModelPostgresProbeConfig,
)


class CheckPostgres(DoctorCheckBase):
    check_id = "postgres"
    check_name = "PostgreSQL"
    category = EnumDoctorCategory.SERVICES

    def run(self) -> ModelDoctorCheckResult:
        start = time.monotonic()
        # Endpoint resolves via the sanctioned overlay boundary
        # (${env.POSTGRES_HOST} / ${env.POSTGRES_PORT}), fail-closed — never a
        # direct os.environ read or localhost default (OMN-13559).
        probe = ModelPostgresProbeConfig.from_overlay()
        host = probe.host
        port = probe.port
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
            message="PostgreSQL accepting connections"
            if ok
            else "PostgreSQL not reachable",
            duration_ms=int((time.monotonic() - start) * 1000),
        )
