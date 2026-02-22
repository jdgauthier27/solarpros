"""Pre-configured retry decorators for common SolarPros operation types.

Built on top of `tenacity <https://tenacity.readthedocs.io/>`_ and tuned
for three distinct categories of work:

* **API calls** -- exponential back-off with jitter, generous retry count.
* **Scraper operations** -- longer base wait (sites may throttle), fewer
  retries.
* **Database operations** -- short wait, limited retries (transient locks
  or connection hiccups only).

Usage::

    from solarpros.utils.retry import retry_api_call, retry_scraper, retry_db

    @retry_api_call
    async def fetch_solar_data(lat: float, lng: float) -> dict:
        ...

    @retry_scraper
    async def scrape_county_records(parcel_id: str) -> dict:
        ...

    @retry_db
    async def save_property(session, data) -> None:
        ...
"""

from __future__ import annotations

import httpx
import structlog
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_exponential_jitter,
    wait_fixed,
)

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Shared logging callback
# ---------------------------------------------------------------------------

def _before_sleep_log(retry_state: RetryCallState) -> None:
    """Log each retry attempt at debug level with structured context."""
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "retrying",
        attempt=retry_state.attempt_number,
        wait=round(retry_state.next_action.sleep, 2) if retry_state.next_action else 0,  # type: ignore[union-attr]
        function=retry_state.fn.__qualname__ if retry_state.fn else "unknown",
        error=str(exception) if exception else None,
        error_type=type(exception).__name__ if exception else None,
    )


# ---------------------------------------------------------------------------
# Exception sets
# ---------------------------------------------------------------------------

# Exceptions that indicate a *transient* HTTP / network issue worth retrying.
_TRANSIENT_HTTP_EXCEPTIONS: tuple[type[BaseException], ...] = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.PoolTimeout,
    ConnectionError,
    TimeoutError,
    OSError,
)

# Exceptions commonly raised by scraper tooling (playwright / httpx / aiohttp).
_SCRAPER_EXCEPTIONS: tuple[type[BaseException], ...] = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadError,
    ConnectionError,
    TimeoutError,
    OSError,
)

# Database-level transient exceptions (asyncpg / SQLAlchemy wrappers).
# We deliberately use broad base classes so that we also catch subclasses
# such as asyncpg.InterfaceError or SA's OperationalError.
try:
    from sqlalchemy.exc import DBAPIError, OperationalError
    _DB_EXCEPTIONS: tuple[type[BaseException], ...] = (
        OperationalError,
        DBAPIError,
        ConnectionError,
        TimeoutError,
        OSError,
    )
except ImportError:  # pragma: no cover
    _DB_EXCEPTIONS = (ConnectionError, TimeoutError, OSError)


# ---------------------------------------------------------------------------
# Pre-configured decorators
# ---------------------------------------------------------------------------

retry_api_call = retry(
    retry=retry_if_exception_type(_TRANSIENT_HTTP_EXCEPTIONS),
    wait=wait_exponential_jitter(initial=1, max=60, jitter=2),
    stop=stop_after_attempt(5),
    before_sleep=_before_sleep_log,
    reraise=True,
)
"""Retry decorator for external API calls.

* **Strategy**: exponential back-off with jitter (1 s -> 60 s cap).
* **Max attempts**: 5
* **Retried exceptions**: transient HTTP / network errors.
"""

retry_scraper = retry(
    retry=retry_if_exception_type(_SCRAPER_EXCEPTIONS),
    wait=wait_exponential(multiplier=2, min=3, max=90),
    stop=stop_after_attempt(3),
    before_sleep=_before_sleep_log,
    reraise=True,
)
"""Retry decorator for web scraper operations.

* **Strategy**: exponential back-off starting at 3 s (cap 90 s).
* **Max attempts**: 3
* **Retried exceptions**: network / timeout errors common during scraping.
"""

retry_db = retry(
    retry=retry_if_exception_type(_DB_EXCEPTIONS),
    wait=wait_fixed(0.5),
    stop=stop_after_attempt(3),
    before_sleep=_before_sleep_log,
    reraise=True,
)
"""Retry decorator for database operations.

* **Strategy**: fixed 0.5 s wait between attempts.
* **Max attempts**: 3
* **Retried exceptions**: transient DB / connection errors.
"""
