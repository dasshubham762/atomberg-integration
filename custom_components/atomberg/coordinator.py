"""Data update coordinator for the Atomberg integration."""

from datetime import timedelta
from logging import getLogger

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import AtombergCloudAPI
from .const import MANUFACTURER
from .udp_listener import UDPListener

_LOGGER = getLogger(__name__)


class AtombergDataUpdateCoordinator(DataUpdateCoordinator):
    """Atomberg data update coordinator."""

    def __init__(self, hass: HomeAssistant, api: AtombergCloudAPI) -> None:
        """Init data update coordinator."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=f"{MANUFACTURER} Coordinator",
            update_interval=timedelta(seconds=30),
        )

        # Start listening to broadcasts
        self.udp_listener = UDPListener(hass, self.async_set_updated_data)
        hass.async_create_task(self.udp_listener.start())

    async def _async_update_data(self):
        """A trigger to update is_online state based on last_seen."""  # noqa: D401
        return {}
