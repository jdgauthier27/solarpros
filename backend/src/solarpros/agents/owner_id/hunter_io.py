"""Hunter.io email finder and verifier client.

Provides both a real HTTP client that calls the Hunter.io API
(https://hunter.io/api-documentation) and a mock client for
development/testing.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

import httpx
import structlog

from solarpros.config import settings

logger = structlog.get_logger()


class BaseHunterIOClient(ABC):
    """Abstract interface for email finder / verification."""

    @abstractmethod
    async def find_email(
        self, domain: str, first_name: str, last_name: str
    ) -> dict | None:
        """Attempt to find an email address for a person at a domain.

        Returns
        -------
        dict | None
            A dict with keys:
                - email (str)
                - score (int): 0-100 confidence score from Hunter
                - first_name (str)
                - last_name (str)
                - position (str | None)
                - domain (str)
            Returns ``None`` if no email could be found.
        """

    @abstractmethod
    async def verify_email(self, email: str) -> dict:
        """Verify whether an email address is valid and deliverable.

        Returns
        -------
        dict
            A dict with keys:
                - email (str)
                - status (str): "valid", "invalid", "accept_all", "unknown"
                - score (int): 0-100 confidence score
                - disposable (bool)
                - webmail (bool)
                - mx_records (bool)
                - smtp_server (bool)
                - smtp_check (bool)
        """


class HunterIOClient(BaseHunterIOClient):
    """Real Hunter.io API client using httpx.

    Requires ``settings.hunter_io_api_key`` to be set.
    """

    BASE_URL = "https://api.hunter.io/v2"
    TIMEOUT = 30.0

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.hunter_io_api_key
        if not self.api_key:
            raise ValueError(
                "Hunter.io API key is required. Set HUNTER_IO_API_KEY in .env"
            )

    async def find_email(
        self, domain: str, first_name: str, last_name: str
    ) -> dict | None:
        logger.info(
            "hunter_find_email_start",
            domain=domain,
            first_name=first_name,
            last_name=last_name,
        )

        params = {
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
            "api_key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            response = await client.get(f"{self.BASE_URL}/email-finder", params=params)

            if response.status_code == 404:
                logger.info("hunter_find_email_not_found", domain=domain)
                return None

            response.raise_for_status()
            data = response.json().get("data", {})

            if not data.get("email"):
                logger.info("hunter_find_email_empty", domain=domain)
                return None

            result = {
                "email": data["email"],
                "score": data.get("score", 0),
                "first_name": data.get("first_name", first_name),
                "last_name": data.get("last_name", last_name),
                "position": data.get("position"),
                "domain": domain,
            }

            logger.info(
                "hunter_find_email_result",
                email=result["email"],
                score=result["score"],
            )
            return result

    async def verify_email(self, email: str) -> dict:
        logger.info("hunter_verify_email_start", email=email)

        params = {
            "email": email,
            "api_key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            response = await client.get(
                f"{self.BASE_URL}/email-verifier", params=params
            )
            response.raise_for_status()
            data = response.json().get("data", {})

            result = {
                "email": data.get("email", email),
                "status": data.get("status", "unknown"),
                "score": data.get("score", 0),
                "disposable": data.get("disposable", False),
                "webmail": data.get("webmail", False),
                "mx_records": data.get("mx_records", False),
                "smtp_server": data.get("smtp_server", False),
                "smtp_check": data.get("smtp_check", False),
            }

            logger.info(
                "hunter_verify_email_result",
                email=email,
                status=result["status"],
                score=result["score"],
            )
            return result


class MockHunterIOClient(BaseHunterIOClient):
    """Mock Hunter.io client that returns realistic data for testing.

    Generates plausible email addresses from the name and domain, and
    returns verification results based on domain characteristics.
    """

    # Domains that simulate "email found" scenarios
    _KNOWN_DOMAINS: dict[str, dict] = {
        "pacificholdings.com": {
            "email": "j.wilson@pacificholdings.com",
            "score": 92,
            "first_name": "James",
            "last_name": "Wilson",
            "position": "Managing Partner",
        },
        "goldenstateprop.com": {
            "email": "m.chen@goldenstateprop.com",
            "score": 88,
            "first_name": "Maria",
            "last_name": "Chen",
            "position": "CEO",
        },
        "sunriserealty.com": {
            "email": "r.patel@sunriserealty.com",
            "score": 95,
            "first_name": "Robert",
            "last_name": "Patel",
            "position": "Principal",
        },
        "coastaldev.com": {
            "email": "d.thompson@coastaldev.com",
            "score": 76,
            "first_name": "David",
            "last_name": "Thompson",
            "position": "Director",
        },
    }

    async def find_email(
        self, domain: str, first_name: str, last_name: str
    ) -> dict | None:
        logger.info(
            "mock_hunter_find_email",
            domain=domain,
            first_name=first_name,
            last_name=last_name,
        )

        # Simulate network latency
        await asyncio.sleep(0.05)

        # Check for known mock domains
        domain_lower = domain.lower()
        if domain_lower in self._KNOWN_DOMAINS:
            result = self._KNOWN_DOMAINS[domain_lower].copy()
            result["domain"] = domain
            return result

        # Generate a plausible email for any domain if we have name parts
        if first_name and last_name:
            first_initial = first_name[0].lower()
            last_lower = last_name.lower().replace(" ", "")
            email = f"{first_initial}.{last_lower}@{domain}"
            return {
                "email": email,
                "score": 72,
                "first_name": first_name,
                "last_name": last_name,
                "position": None,
                "domain": domain,
            }

        # No name parts provided -- cannot generate
        logger.info("mock_hunter_find_email_not_found", domain=domain)
        return None

    async def verify_email(self, email: str) -> dict:
        logger.info("mock_hunter_verify_email", email=email)

        # Simulate network latency
        await asyncio.sleep(0.05)

        # Extract domain from email
        domain = email.rsplit("@", 1)[-1].lower() if "@" in email else ""

        # Known domains get "valid" status
        if domain in self._KNOWN_DOMAINS:
            return {
                "email": email,
                "status": "valid",
                "score": 95,
                "disposable": False,
                "webmail": False,
                "mx_records": True,
                "smtp_server": True,
                "smtp_check": True,
            }

        # Webmail domains get "accept_all" status
        webmail_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com"}
        if domain in webmail_domains:
            return {
                "email": email,
                "status": "accept_all",
                "score": 65,
                "disposable": False,
                "webmail": True,
                "mx_records": True,
                "smtp_server": True,
                "smtp_check": False,
            }

        # Default: plausible but unverified
        return {
            "email": email,
            "status": "valid",
            "score": 80,
            "disposable": False,
            "webmail": False,
            "mx_records": True,
            "smtp_server": True,
            "smtp_check": True,
        }
