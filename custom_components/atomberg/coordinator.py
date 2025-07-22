"""Data update coordinator for the Atomberg integration."""

from logging import getLogger

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import AtombergCloudAPI
from .const import MANUFACTURER
from .device import AtombergDevice
from .udp_listener import UDPListener

_LOGGER = getLogger(__name__)


class AtombergDataUpdateCoordinator(DataUpdateCoordinator):
    """Atomberg data update coordinator."""

    def __init__(
        self, hass: HomeAssistant, api: AtombergCloudAPI, udp_listener: UDPListener
    ) -> None:
        """Init data update coordinator."""
        self.api = api
        self.udp_listener = udp_listener
        super().__init__(hass, _LOGGER, name=f"{MANUFACTURER} Coordinator")

        # Set callback on udp listener
        self.udp_listener.set_callback(self.async_set_updated_data)

    def get_devices(self) -> list[AtombergDevice]:
        """Get list of available devices."""
        return [
            AtombergDevice(data=data, api=self.api, config_entry=self.config_entry)
            for data in self.api.device_list.values()
        ]
