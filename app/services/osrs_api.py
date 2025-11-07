import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import quote

from aiohttp import ClientError, ClientSession, ClientTimeout
from pydantic import BaseModel, Field

from app.exceptions import (
    APIUnavailableError,
    OSRSAPIError,
    OSRSPlayerNotFoundError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class HiscoreData(BaseModel):
    """Parsed hiscore data from OSRS API."""

    overall: Dict[str, Optional[int]] = Field(description="Overall stats")
    skills: Dict[str, Dict[str, Optional[int]]] = Field(
        description="Individual skill stats"
    )
    bosses: Dict[str, Dict[str, Optional[int]]] = Field(
        description="Boss kill counts"
    )
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class OSRSAPIClient:
    """Async HTTP client for OSRS Hiscores API."""

    BASE_URL = (
        "https://secure.runescape.com/m=hiscore_oldschool/index_lite.json"
    )

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0
    MAX_BACKOFF = 30.0
    BACKOFF_MULTIPLIER = 2.0

    # Timeout configuration (seconds)
    TIMEOUT = 30.0

    def __init__(self) -> None:
        """Initialize the OSRS API client."""
        self._session: Optional[ClientSession] = None

    async def __aenter__(self) -> "OSRSAPIClient":
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(
        self, exc_type: Any, exc_val: Any, exc_tb: Any
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure HTTP session is created."""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=self.TIMEOUT)

            self._session = ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "OSRSDiff/1.0.0 (https://github.com/mchestr/osrsdiff)"
                },
            )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _make_request(self, username: str) -> Dict[str, Any]:
        """Make HTTP request to OSRS API with retry logic."""
        await self._ensure_session()
        assert self._session is not None

        url = f"{self.BASE_URL}?player={quote(username)}"

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                logger.debug(
                    f"Fetching hiscores for {username} (attempt {attempt + 1})"
                )

                async with self._session.get(url) as response:
                    if response.status == 200:
                        try:
                            json_data: Dict[str, Any] = await response.json()
                            if not json_data:
                                raise OSRSPlayerNotFoundError(username)
                            return json_data
                        except OSRSPlayerNotFoundError:
                            raise
                        except Exception as e:
                            raise OSRSAPIError(
                                f"Failed to parse JSON response: {e}"
                            )

                    elif response.status == 404:
                        raise OSRSPlayerNotFoundError(username)

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

    def _parse_skill_data(
        self, skill_data: Dict[str, Any]
    ) -> Dict[str, Optional[int]]:
        """Parse skill data from JSON format."""
        try:
            return {
                "rank": (
                    skill_data.get("rank")
                    if skill_data.get("rank", -1) != -1
                    else None
                ),
                "level": (
                    skill_data.get("level")
                    if skill_data.get("level", -1) != -1
                    else None
                ),
                "experience": (
                    skill_data.get("xp")
                    if skill_data.get("xp", -1) != -1
                    else None
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
            raise OSRSAPIError(
                "Invalid hiscore data format: expected JSON object"
            )

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
                    skill_data.get("rank")
                    if skill_data.get("rank", -1) != -1
                    else None
                ),
                "level": (
                    skill_data.get("level")
                    if skill_data.get("level", -1) != -1
                    else None
                ),
                "experience": (
                    skill_data.get("xp")
                    if skill_data.get("xp", -1) != -1
                    else None
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
            OSRSPlayerNotFoundError: If player is not found
            RateLimitError: If rate limit is exceeded (from API)
            APIUnavailableError: If API is unavailable
            OSRSAPIError: For other API errors
        """
        if not username or not username.strip():
            raise ValueError("Username cannot be empty")

        username = username.strip()

        try:
            json_data = await self._make_request(username)
            return self._parse_hiscore_data(json_data)

        except (OSRSPlayerNotFoundError, RateLimitError, APIUnavailableError):
            # Re-raise known exceptions
            raise

        except Exception as e:
            logger.error(
                f"Unexpected error fetching hiscores for {username}: {e}"
            )
            raise OSRSAPIError(f"Failed to fetch hiscores: {e}")

    async def check_player_exists(self, username: str) -> bool:
        """
        Check if a player exists in OSRS hiscores.

        Args:
            username: OSRS player username

        Returns:
            bool: True if player exists, False otherwise

        Raises:
            RateLimitError: If rate limit is exceeded
            APIUnavailableError: If API is unavailable
            OSRSAPIError: For other API errors
        """
        try:
            await self.fetch_player_hiscores(username)
            return True
        except OSRSPlayerNotFoundError:
            return False
        except (RateLimitError, APIUnavailableError, OSRSAPIError):
            # For other errors, we can't determine existence
            raise


# Global client instance for dependency injection
osrs_api_client = OSRSAPIClient()


async def get_osrs_api_client() -> OSRSAPIClient:
    """Dependency injection function for FastAPI."""
    return osrs_api_client
