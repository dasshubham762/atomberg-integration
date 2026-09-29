"""Data update coordinator for the Atomberg integration."""

from datetime import timedelta
from logging import getLogger

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import AtombergCloudAPI
from .const import DEFAULT_POLLING_INTERVAL, MANUFACTURER
from .device import AtombergDevice
from .udp_listener import UDPListener

_LOGGER = getLogger(__name__)


class AtombergDataUpdateCoordinator(DataUpdateCoordinator):
    """Atomberg data update coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: AtombergCloudAPI,
        udp_listener: UDPListener | None,
        *,
        use_polling: bool = False,
        polling_interval: int = DEFAULT_POLLING_INTERVAL,
    ) -> None:
        """Init data update coordinator.

        In broadcast mode the coordinator is push-driven: device state is updated
        from UDP broadcasts received by ``udp_listener``. In polling mode the
        coordinator periodically fetches device state from the cloud API instead,
        which works even when Home Assistant cannot receive the local broadcasts
        (e.g. when the fans live on a different VLAN).
        """
        super().__init__(
            hass,
            _LOGGER,
            name=f"{MANUFACTURER} Coordinator",
            update_interval=(
                timedelta(seconds=polling_interval) if use_polling else None
            ),
        )

        self.api = api
        self.udp_listener = udp_listener
        self.use_polling = use_polling
        self.devices = [
            AtombergDevice(data=data, api=self.api, config_entry=self.config_entry)
            for data in self.api.device_list.values()
        ]

        # In broadcast mode, update device state from incoming UDP broadcasts.
        if not use_polling and udp_listener is not None:
            udp_listener.add_callback(self.config_entry, self.async_set_updated_data)

    async def _async_update_data(self) -> dict[str, dict]:
        """Fetch device state from the cloud API (polling mode only).

        Only invoked when ``update_interval`` is set, i.e. in polling mode.
        Returns a mapping of ``device_id`` to its (decoded) state.
        """
        try:
            states = await self.api.async_get_device_state(force_offline=False)
        except Exception as err:
            raise UpdateFailed(f"Error fetching device state: {err}") from err

        if states is None:
            raise UpdateFailed("Failed to fetch device state from Atomberg cloud")

        return {state["device_id"]: state for state in states}
