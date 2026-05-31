"""Data update coordinator for the Atomberg integration."""

from logging import getLogger

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import AtombergCloudAPI
from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_SERIES,
    CONF_DISPLAY_NAME,
    MANUFACTURER,
    UNKNOWN_SERIES,
)
from .device import (
    ATTR_BRIGHTNESS,
    ATTR_IS_ONLINE,
    ATTR_LED,
    ATTR_LIGHT_MODE,
    ATTR_POWER,
    ATTR_SLEEP,
    ATTR_SPEED,
    ATTR_TIMER_HOURS,
    ATTR_TIMER_TIME_ELAPSED_MINS,
    LIGHT_MODE_DAYLIGHT,
    AtombergDevice,
)
from .udp_listener import UDPListener

_LOGGER = getLogger(__name__)

_LOCAL_INITIAL_STATE = {
    ATTR_POWER: False,
    ATTR_LED: False,
    ATTR_SLEEP: False,
    ATTR_SPEED: 1,
    ATTR_TIMER_HOURS: 0,
    ATTR_TIMER_TIME_ELAPSED_MINS: 0,
    ATTR_IS_ONLINE: False,
    ATTR_BRIGHTNESS: 1,
    ATTR_LIGHT_MODE: LIGHT_MODE_DAYLIGHT,
}


class AtombergDataUpdateCoordinator(DataUpdateCoordinator):
    """Atomberg data update coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: AtombergCloudAPI | None,
        udp_listener: UDPListener,
        config_entry: ConfigEntry,
    ) -> None:
        """Init data update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{MANUFACTURER} Coordinator",
        )

        self.api = api
        self.udp_listener = udp_listener

        if api is not None:
            # Cloud mode: build device list from API inventory.
            self.devices = [
                AtombergDevice(data=data, api=api, config_entry=config_entry)
                for data in api.device_list.values()
            ]
        else:
            # Local UDP mode: single device from config entry data.
            cfg = config_entry
            self.devices = [
                AtombergDevice(
                    data={
                        "device_id": cfg.data[CONF_DEVICE_ID],
                        "name": cfg.data[CONF_DISPLAY_NAME],
                        "series": cfg.data.get(CONF_DEVICE_SERIES, UNKNOWN_SERIES),
                        "model": "Atomberg Fan",
                        "state": dict(_LOCAL_INITIAL_STATE),
                    },
                    api=None,
                    config_entry=cfg,
                )
            ]

        # Add callback on udp listener
        self.udp_listener.add_callback(config_entry, self.async_set_updated_data)
