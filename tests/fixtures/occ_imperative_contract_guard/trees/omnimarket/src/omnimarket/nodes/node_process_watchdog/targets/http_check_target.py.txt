"""TargetHttp — generic HTTP GET health check with configurable timeout.

Status mapping:
  HEALTHY  — 2xx response
  DEGRADED — non-2xx response (server responded but unhealthy)
  DOWN     — connection refused, timeout, DNS failure
  UNKNOWN  — unexpected error
"""

from __future__ import annotations

import urllib.error
import urllib.request

from omnimarket.nodes.node_process_watchdog.models.model_watchdog_state import (
    EnumCheckStatus,
    EnumCheckTarget,
    ModelWatchdogCheckResult,
)


class TargetHttp:
    def __init__(
        self,
        name: str,
        url: str,
        timeout: float = 5.0,
        category: EnumCheckTarget = EnumCheckTarget.LLM_ENDPOINTS,
    ) -> None:
        if not name:
            raise ValueError("name must be non-empty")
        if not url:
            raise ValueError("url must be non-empty")
        if timeout <= 0:
            raise ValueError("timeout must be > 0")
        self._name = name
        self._url = url
        self._timeout = timeout
        self._category = category

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> EnumCheckTarget:
        return self._category

    def check(self) -> ModelWatchdogCheckResult:
        try:
            req = urllib.request.Request(self._url, method="GET")
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if 200 <= resp.status < 300:
                    return ModelWatchdogCheckResult(
                        target=self._name,
                        category=self._category,
                        status=EnumCheckStatus.HEALTHY,
                        message=f"HTTP {self._url} returned {resp.status}",
                    )
                return ModelWatchdogCheckResult(
                    target=self._name,
                    category=self._category,
                    status=EnumCheckStatus.DEGRADED,
                    message=f"HTTP {self._url} returned {resp.status}",
                    details={"status_code": resp.status},
                )
        except urllib.error.HTTPError as e:
            return ModelWatchdogCheckResult(
                target=self._name,
                category=self._category,
                status=EnumCheckStatus.DEGRADED,
                message=f"HTTP {self._url} returned {e.code}",
                details={"status_code": e.code},
            )
        except urllib.error.URLError as e:
            return ModelWatchdogCheckResult(
                target=self._name,
                category=self._category,
                status=EnumCheckStatus.DOWN,
                message=f"HTTP {self._url} unreachable: {e.reason}",
            )
        except TimeoutError:
            return ModelWatchdogCheckResult(
                target=self._name,
                category=self._category,
                status=EnumCheckStatus.DOWN,
                message=f"HTTP {self._url} timed out after {self._timeout}s",
            )
        except Exception as e:
            return ModelWatchdogCheckResult(
                target=self._name,
                category=self._category,
                status=EnumCheckStatus.UNKNOWN,
                message=f"HTTP check error: {e}",
            )

    def restart(self) -> bool:
        return False


__all__: list[str] = ["TargetHttp"]
