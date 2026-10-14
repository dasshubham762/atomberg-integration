"""Polling coordinator for Atomberg water purifiers."""

from datetime import timedelta
from logging import getLogger

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApiError, AtombergCloudAPI, QuotaExceeded
from .const import MANUFACTURER
from .device import AtombergPurifier

_LOGGER = getLogger(__name__)


class AtombergPurifierCoordinator(DataUpdateCoordinator[dict[str, dict]]):
    """Atomberg water purifier coordinator.

    Purifiers don't broadcast their state over UDP, so it has to be polled
    from the cloud. One poll fetches all purifiers in a single API call.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: AtombergCloudAPI,
        devices: list[AtombergPurifier],
        poll_interval_mins: int,
    ) -> None:
        """Init purifier coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{MANUFACTURER} Purifier Coordinator",
            update_interval=timedelta(minutes=poll_interval_mins),
        )

        self.api = api
        self.devices = devices

    async def _async_update_data(self) -> dict[str, dict]:
        """Fetch purifier states from the cloud."""
        try:
            states = await self.api.async_get_purifier_states()
        except QuotaExceeded as e:
            raise UpdateFailed(
                "Atomberg API daily quota exhausted. "
                "Consider increasing the purifier polling interval."
            ) from e
        except ApiError as e:
            raise UpdateFailed(str(e)) from e
        except Exception as e:
            raise UpdateFailed(f"Failed to fetch purifier states: {e}") from e

        for device in self.devices:
            if (state := states.get(device.id)) is not None:
                device.set_state(state)

        return states
