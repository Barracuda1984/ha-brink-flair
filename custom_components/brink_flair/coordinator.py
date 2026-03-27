"""DataUpdateCoordinator for Brink Flair."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class BrinkFlairCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manages fetching data from the Brink Flair device."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        """Initialize the coordinator."""
        self.host = host
        self.port = port

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the device."""
        try:
            # TODO: replace with actual API/client call
            return await self._fetch_data()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    async def _fetch_data(self) -> dict[str, Any]:
        """Fetch raw data from the Brink Flair device."""
        # TODO: implement device communication
        raise NotImplementedError
