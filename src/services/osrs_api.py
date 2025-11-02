"""OSRS Hiscores API client service."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any
from urllib.parse import quote

import aiohttp
from aiohttp import ClientTimeout, ClientSession, ClientError
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OSRSAPIError(Exception):
    """Base exception for OSRS API errors."""

    pass


class PlayerNotFoundError(OSRSAPIError):
    """Raised when a player is not found in OSRS hiscores."""

    pass


class RateLimitError(OSRSAPIError):
    """Raised when rate limit is exceeded."""

    pass


class APIUnavailableError(OSRSAPIError):
    """Raised when OSRS API is unavailable."""

    pass


class HiscoreData(BaseModel):
    """Parsed hiscore data from OSRS API."""

    overall: Dict[str, Optional[int]] = Field(description="Overall stats")
    skills: Dict[str, Dict[str, Optional[int]]] = Field(
        description="Individual skill stats"
    )
    bosses: Dict[str, Dict[str, Optional[int]]] = Field(description="Boss kill counts")
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OSRSAPIClient:
    """Async HTTP client for OSRS Hiscores API."""

    BASE_URL = "https://secure.runescape.com/m=hiscore_oldschool/index_lite.json"

    # OSRS API rate limiting: 1 request per 2 seconds to be safe
    RATE_LIMIT_DELAY = 2.0

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0
    MAX_BACKOFF = 30.0
    BACKOFF_MULTIPLIER = 2.0

    # Timeout configuration
    CONNECT_TIMEOUT = 10.0
    READ_TIMEOUT = 30.0
    TOTAL_TIMEOUT = 60.0

    def __init__(self) -> None:
        """Initialize the OSRS API client."""
        self._session: Optional[ClientSession] = None
        self._last_request_time: Optional[datetime] = None
        self._rate_limit_lock = asyncio.Lock()

    async def __aenter__(self) -> "OSRSAPIClient":
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure HTTP session is created."""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(
                connect=self.CONNECT_TIMEOUT,
                sock_read=self.READ_TIMEOUT,
                total=self.TOTAL_TIMEOUT,
            )

            connector = aiohttp.TCPConnector(
                limit=10,  # Total connection pool size
                limit_per_host=5,  # Connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )

            self._session = ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    "User-Agent": "OSRS-Diff/1.0.0 (https://github.com/osrs-diff/backend)"
                },
            )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        async with self._rate_limit_lock:
            if self._last_request_time is not None:
                time_since_last = datetime.now(timezone.utc) - self._last_request_time
                if time_since_last.total_seconds() < self.RATE_LIMIT_DELAY:
                    sleep_time = self.RATE_LIMIT_DELAY - time_since_last.total_seconds()
                    logger.debug(
                        f"Rate limiting: sleeping for {sleep_time:.2f} seconds"
                    )
                    await asyncio.sleep(sleep_time)

            self._last_request_time = datetime.now(timezone.utc)

    async def _make_request(self, username: str) -> Dict[str, Any]:
        """Make HTTP request to OSRS API with retry logic."""
        await self._ensure_session()
        assert self._session is not None

        url = f"{self.BASE_URL}?player={quote(username)}"

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                await self._enforce_rate_limit()

                logger.debug(
                    f"Fetching hiscores for {username} (attempt {attempt + 1})"
                )

                async with self._session.get(url) as response:
                    if response.status == 200:
                        try:
                            json_data: Dict[str, Any] = await response.json()
                            if not json_data:
                                raise PlayerNotFoundError(
                                    f"Player '{username}' not found"
                                )
                            return json_data
                        except Exception as e:
                            raise OSRSAPIError(f"Failed to parse JSON response: {e}")

                    elif response.status == 404:
                        raise PlayerNotFoundError(f"Player '{username}' not found")

                    elif response.status == 429:
                        raise RateLimitError("Rate limit exceeded")

                    elif response.status >= 500:
                        raise APIUnavailableError(
                            f"OSRS API unavailable (status: {response.status})"
                        )

                    else:
                        raise OSRSAPIError(
                            f"Unexpected response status: {response.status}"
                        )

            except (ClientError, asyncio.TimeoutError) as e:
                if attempt == self.MAX_RETRIES:
                    raise APIUnavailableError(
                        f"Failed to fetch data after {self.MAX_RETRIES + 1} attempts: {e}"
                    )

                # Calculate exponential backoff delay
                backoff_delay = min(
                    self.INITIAL_BACKOFF * (self.BACKOFF_MULTIPLIER**attempt),
                    self.MAX_BACKOFF,
                )

                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.MAX_RETRIES + 1}): {e}. "
                    f"Retrying in {backoff_delay:.2f} seconds"
                )

                await asyncio.sleep(backoff_delay)

        # This should never be reached due to the loop logic above
        raise APIUnavailableError("Unexpected error in retry logic")

    def _parse_skill_data(self, skill_data: Dict[str, Any]) -> Dict[str, Optional[int]]:
        """Parse skill data from JSON format."""
        try:
            return {
                "rank": (
                    skill_data.get("rank") if skill_data.get("rank", -1) != -1 else None
                ),
                "level": (
                    skill_data.get("level")
                    if skill_data.get("level", -1) != -1
                    else None
                ),
                "experience": (
                    skill_data.get("xp") if skill_data.get("xp", -1) != -1 else None
                ),
            }
        except (ValueError, TypeError):
            return {"rank": None, "level": None, "experience": None}

    def _parse_activity_data(
        self, activity_data: Dict[str, Any]
    ) -> Dict[str, Optional[int]]:
        """Parse activity/boss data from JSON format."""
        try:
            return {
                "rank": (
                    activity_data.get("rank")
                    if activity_data.get("rank", -1) != -1
                    else None
                ),
                "kc": (
                    activity_data.get("score")
                    if activity_data.get("score", -1) != -1
                    else None
                ),
            }
        except (ValueError, TypeError):
            return {"rank": None, "kc": None}

    def _parse_hiscore_data(self, json_data: Dict[str, Any]) -> HiscoreData:
        """Parse OSRS hiscore JSON data into structured format."""
        if not isinstance(json_data, dict):
            raise OSRSAPIError("Invalid hiscore data format: expected JSON object")

        # Parse skills (list format)
        skills_list = json_data.get("skills", [])
        if not isinstance(skills_list, list):
            raise OSRSAPIError("Invalid skills data format: expected list")

        skills: Dict[str, Dict[str, Optional[int]]] = {}
        overall: Dict[str, Optional[int]] = {
            "rank": None,
            "level": None,
            "experience": None,
        }

        for skill_data in skills_list:
            if not isinstance(skill_data, dict):
                continue

            skill_name = skill_data.get("name", "").lower().replace(" ", "_")
            parsed_skill = {
                "rank": (
                    skill_data.get("rank") if skill_data.get("rank", -1) != -1 else None
                ),
                "level": (
                    skill_data.get("level")
                    if skill_data.get("level", -1) != -1
                    else None
                ),
                "experience": (
                    skill_data.get("xp") if skill_data.get("xp", -1) != -1 else None
                ),
            }

            if skill_name == "overall":
                overall = parsed_skill
            else:
                skills[skill_name] = parsed_skill

        # Parse activities/bosses (list format)
        activities_list = json_data.get("activities", [])
        if not isinstance(activities_list, list):
            raise OSRSAPIError("Invalid activities data format: expected list")

        bosses: Dict[str, Dict[str, Optional[int]]] = {}

        for activity_data in activities_list:
            if not isinstance(activity_data, dict):
                continue

            activity_name = (
                activity_data.get("name", "")
                .lower()
                .replace(" ", "_")
                .replace("-", "_")
            )
            parsed_activity = {
                "rank": (
                    activity_data.get("rank")
                    if activity_data.get("rank", -1) != -1
                    else None
                ),
                "kc": (
                    activity_data.get("score")
                    if activity_data.get("score", -1) != -1
                    else None
                ),
            }

            bosses[activity_name] = parsed_activity

        return HiscoreData(overall=overall, skills=skills, bosses=bosses)

    async def fetch_player_hiscores(self, username: str) -> HiscoreData:
        """
        Fetch hiscore data for a player from OSRS API.

        Args:
            username: OSRS player username

        Returns:
            HiscoreData: Parsed hiscore data

        Raises:
            PlayerNotFoundError: If player is not found
            RateLimitError: If rate limit is exceeded
            APIUnavailableError: If API is unavailable
            OSRSAPIError: For other API errors
        """
        if not username or not username.strip():
            raise ValueError("Username cannot be empty")

        username = username.strip()

        try:
            json_data = await self._make_request(username)
            return self._parse_hiscore_data(json_data)

        except (PlayerNotFoundError, RateLimitError, APIUnavailableError):
            # Re-raise known exceptions
            raise

        except Exception as e:
            logger.error(f"Unexpected error fetching hiscores for {username}: {e}")
            raise OSRSAPIError(f"Failed to fetch hiscores: {e}")

    async def check_player_exists(self, username: str) -> bool:
        """
        Check if a player exists in OSRS hiscores.

        Args:
            username: OSRS player username

        Returns:
            bool: True if player exists, False otherwise
        """
        try:
            await self.fetch_player_hiscores(username)
            return True
        except PlayerNotFoundError:
            return False
        except (RateLimitError, APIUnavailableError, OSRSAPIError):
            # For other errors, we can't determine existence
            raise


# Global client instance for dependency injection
osrs_api_client = OSRSAPIClient()


async def get_osrs_api_client() -> OSRSAPIClient:
    """Dependency injection function for FastAPI."""
    return osrs_api_client
