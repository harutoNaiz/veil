"""Virtual clock in integer milliseconds; it never goes back."""

from __future__ import annotations


class VirtualClock:
    def __init__(self, t0_ms: int = 0) -> None:
        self._t = t0_ms

    def now(self) -> int:
        return self._t

    def advance_to(self, t_ms: int) -> int:
        self._t = max(self._t, t_ms)
        return self._t
