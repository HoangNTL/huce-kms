import logging
import time
from typing import Any

logger = logging.getLogger("huce_kms.ai.cooldown")


class CooldownTracker:
    """Thread-safe circuit breaker tracker that puts failing providers on cooldown."""

    def __init__(self, default_cooldown_seconds: int = 900):
        self.default_cooldown_seconds = default_cooldown_seconds
        self._cooldowns: dict[str, float] = {}

    def set_cooldown(
        self, provider: str, duration_seconds: int | None = None, reason: str = ""
    ) -> None:
        """Mark a provider as unavailable until current_time + duration."""
        duration = duration_seconds or self.default_cooldown_seconds
        expires_at = time.time() + duration
        self._cooldowns[provider] = expires_at
        logger.warning(
            "[CIRCUIT_BREAKER] Provider '%s' put on cooldown for %ds (until %.0f). Reason: %s",
            provider,
            duration,
            expires_at,
            reason,
        )

    def is_in_cooldown(self, provider: str) -> bool:
        """Check if a provider is currently cooled down."""
        expires_at = self._cooldowns.get(provider)
        if not expires_at:
            return False

        if time.time() >= expires_at:
            # Cooldown expired, clear and return False
            del self._cooldowns[provider]
            logger.info("[CIRCUIT_BREAKER] Cooldown expired for provider '%s'. Restoring to active.", provider)
            return False

        return True

    def get_remaining_seconds(self, provider: str) -> int:
        """Return remaining seconds of cooldown for a provider, or 0 if active."""
        expires_at = self._cooldowns.get(provider)
        if not expires_at:
            return 0
        remaining = int(expires_at - time.time())
        return max(0, remaining)

    def get_remaining_cooldown(self, provider: str) -> int:
        """Alias for get_remaining_seconds."""
        return self.get_remaining_seconds(provider)

    def reset(self, provider: str | None = None) -> None:
        """Manually clear cooldown for one or all providers."""
        if provider:
            self._cooldowns.pop(provider, None)
        else:
            self._cooldowns.clear()

    def clear_all(self) -> None:
        """Clear all provider cooldowns."""
        self.reset()

    def clear_cooldown(self, provider: str) -> None:
        """Clear cooldown for a specific provider."""
        self.reset(provider)

    def get_status_report(self) -> dict[str, dict[str, Any]]:
        """Return status summary for all tracked providers."""
        now = time.time()
        report = {}
        for p, exp in list(self._cooldowns.items()):
            if now < exp:
                report[p] = {
                    "status": "cooldown",
                    "remaining_seconds": int(exp - now),
                }
            else:
                self._cooldowns.pop(p, None)
        return report


# Global instance
cooldown_tracker = CooldownTracker()
