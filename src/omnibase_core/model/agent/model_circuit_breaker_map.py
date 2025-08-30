"""Model for managing circuit breakers."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from omnibase_core.patterns.circuit_breaker import CircuitBreaker


class ModelCircuitBreakerMap(BaseModel):
    """
    Strongly-typed mapping for circuit breaker management.

    Replaces Dict[str, CircuitBreaker] to comply with ONEX
    standards requiring specific typed models.
    """

    breakers: Dict[str, CircuitBreaker] = Field(
        default_factory=dict, description="Map of service names to circuit breakers"
    )

    class Config:
        # Allow CircuitBreaker objects in Pydantic model
        arbitrary_types_allowed = True

    def add_breaker(self, service_name: str, breaker: CircuitBreaker) -> None:
        """Add a circuit breaker for a service."""
        self.breakers[service_name] = breaker

    def get_breaker(self, service_name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker for a specific service."""
        return self.breakers.get(service_name)

    def remove_breaker(self, service_name: str) -> bool:
        """Remove a circuit breaker."""
        if service_name in self.breakers:
            del self.breakers[service_name]
            return True
        return False

    def get_open_breakers(self) -> List[str]:
        """Get list of services with open circuit breakers."""
        open_services = []
        for service_name, breaker in self.breakers.items():
            if breaker.is_open:
                open_services.append(service_name)
        return open_services

    def get_closed_breakers(self) -> List[str]:
        """Get list of services with closed circuit breakers."""
        closed_services = []
        for service_name, breaker in self.breakers.items():
            if breaker.is_closed:
                closed_services.append(service_name)
        return closed_services

    def get_half_open_breakers(self) -> List[str]:
        """Get list of services with half-open circuit breakers."""
        half_open_services = []
        for service_name, breaker in self.breakers.items():
            if breaker.is_half_open:
                half_open_services.append(service_name)
        return half_open_services

    def reset_breaker(self, service_name: str) -> bool:
        """Reset a circuit breaker to closed state."""
        breaker = self.get_breaker(service_name)
        if breaker:
            breaker.reset()
            return True
        return False

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self.breakers.values():
            breaker.reset()

    def count(self) -> int:
        """Get total number of circuit breakers."""
        return len(self.breakers)

    def get_health_summary(self) -> Dict[str, int]:
        """Get summary of circuit breaker states."""
        return {
            "open": len(self.get_open_breakers()),
            "closed": len(self.get_closed_breakers()),
            "half_open": len(self.get_half_open_breakers()),
            "total": self.count(),
        }

    def clear(self) -> None:
        """Remove all circuit breakers."""
        self.breakers.clear()
