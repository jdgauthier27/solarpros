"""Circuit breaker pattern for protecting external service calls.

Implements the classic three-state model:

* **CLOSED** -- requests flow through normally.  Failures are counted and,
  once they reach *failure_threshold*, the circuit transitions to OPEN.
* **OPEN** -- all requests are rejected immediately with
  :class:`CircuitBreakerOpen`.  After *recovery_timeout* seconds the circuit
  moves to HALF_OPEN.
* **HALF_OPEN** -- a limited number of probe requests are allowed through.
  If they succeed the circuit returns to CLOSED; if any fail it returns to
  OPEN.
"""

from __future__ import annotations

import asyncio
import enum
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpen(Exception):
    """Raised when a call is attempted while the circuit is OPEN."""

    def __init__(self, circuit_name: str, retry_after: float) -> None:
        self.circuit_name = circuit_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit '{circuit_name}' is OPEN. Retry after {retry_after:.1f}s"
        )


class CircuitBreaker:
    """Async-aware circuit breaker.

    Parameters
    ----------
    name:
        A human-friendly name for logging and exception messages.
    failure_threshold:
        Number of consecutive failures in the CLOSED state before the
        circuit trips to OPEN.  Defaults to ``5``.
    recovery_timeout:
        Seconds to wait in the OPEN state before transitioning to
        HALF_OPEN.  Defaults to ``30``.
    half_open_max_calls:
        Maximum number of concurrent probe requests allowed while
        HALF_OPEN.  Defaults to ``1``.
    excluded_exceptions:
        A tuple of exception types that should **not** be counted as
        failures (e.g. client-side validation errors).
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
        excluded_exceptions: tuple[type[BaseException], ...] = (),
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.excluded_exceptions = excluded_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._half_open_calls: int = 0
        self._last_failure_time: float = 0.0
        self._opened_at: float = 0.0
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Return the current state, lazily promoting OPEN -> HALF_OPEN."""
        if self._state is CircuitState.OPEN:
            if time.monotonic() - self._opened_at >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute *func* through the circuit breaker.

        Parameters
        ----------
        func:
            An async callable to invoke.
        *args, **kwargs:
            Positional and keyword arguments forwarded to *func*.

        Returns
        -------
        T
            The return value of *func*.

        Raises
        ------
        CircuitBreakerOpen
            If the circuit is OPEN and the recovery timeout has not
            elapsed.
        """
        async with self._lock:
            self._pre_call_check()

        try:
            result = await func(*args, **kwargs)
        except BaseException as exc:
            if isinstance(exc, self.excluded_exceptions):
                raise
            async with self._lock:
                self._record_failure()
            raise
        else:
            async with self._lock:
                self._record_success()
            return result

    async def reset(self) -> None:
        """Manually reset the circuit to CLOSED."""
        async with self._lock:
            self._transition_to(CircuitState.CLOSED)

    # ------------------------------------------------------------------
    # Internal state machine helpers (must be called while holding _lock)
    # ------------------------------------------------------------------

    def _pre_call_check(self) -> None:
        """Decide whether the call is permitted; raise otherwise."""
        state = self.state  # triggers lazy OPEN -> HALF_OPEN promotion

        if state is CircuitState.CLOSED:
            return

        if state is CircuitState.OPEN:
            retry_after = self.recovery_timeout - (
                time.monotonic() - self._opened_at
            )
            raise CircuitBreakerOpen(self.name, max(0.0, retry_after))

        # HALF_OPEN -- allow only a limited number of probe calls.
        if self._half_open_calls >= self.half_open_max_calls:
            raise CircuitBreakerOpen(self.name, retry_after=0.0)
        self._half_open_calls += 1

    def _record_success(self) -> None:
        if self._state is CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_max_calls:
                self._transition_to(CircuitState.CLOSED)
        else:
            # CLOSED -- reset the consecutive-failure counter.
            self._failure_count = 0

    def _record_failure(self) -> None:
        self._last_failure_time = time.monotonic()

        if self._state is CircuitState.HALF_OPEN:
            # Any failure while probing sends us back to OPEN.
            logger.warning(
                "circuit_breaker_half_open_failure",
                circuit=self.name,
            )
            self._transition_to(CircuitState.OPEN)
            return

        # CLOSED state
        self._failure_count += 1
        logger.debug(
            "circuit_breaker_failure",
            circuit=self.name,
            failure_count=self._failure_count,
            threshold=self.failure_threshold,
        )
        if self._failure_count >= self.failure_threshold:
            self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        old_state = self._state
        self._state = new_state

        if new_state is CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
        elif new_state is CircuitState.OPEN:
            self._opened_at = time.monotonic()
            self._half_open_calls = 0
            self._success_count = 0
        elif new_state is CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0

        if old_state is not new_state:
            logger.info(
                "circuit_breaker_state_change",
                circuit=self.name,
                from_state=old_state.value,
                to_state=new_state.value,
            )
