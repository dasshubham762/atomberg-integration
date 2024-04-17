"""Base Atomberg entity."""

from datetime import datetime, timedelta
from logging import getLogger

from homeassistant.const import Platform
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import utcnow

from .const import DOMAIN, MANUFACTURER
from .coordinator import AtombergDataUpdateCoordinator
from .device import AtombergDevice

AVAILABILITY_TIMEOUT = 10  # Seconds
_LOGGER = getLogger(__name__)


class AtombergEntity(CoordinatorEntity, Entity):
    """Atomberg base entity."""

    def __init__(
        self, coordinator: AtombergDataUpdateCoordinator, device: AtombergDevice
    ) -> None:
        """Init Atomberg base entity."""
        super().__init__(coordinator)

        self.hass = coordinator.hass
        self._device = device
        self._attr_device_state = self._device.state
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._get_unique_id())},
            name=self._device.name,
            manufacturer=MANUFACTURER,
            model=self._device.model,
        )

        # Refresh availability on fixed interval
        async_track_time_interval(
            self.hass, self._refresh_availability, timedelta(seconds=30)
        )

    def _get_unique_id(
        self, platform: Platform | None = None, suffix: str | None = None
    ):
        unique_id = f"{MANUFACTURER}.{self._device.id}"
        if suffix:
            unique_id += f"_{suffix}"
        if platform:
            unique_id += f"_{platform}"
        return unique_id

    @property
    def available(self) -> bool:
        """Whether the entity is online."""
        return self.device_state["is_online"]

    @property
    def device_state(self) -> dict:
        """Get device state."""
        return self._attr_device_state

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data["device_id"] != self._device.id:
            return

        state = {}
        # Decode the state data
        if state_string := self.coordinator.data.get("state_string"):
            value = int(state_string.split(",")[0])

            state.update(
                {
                    "power": (0x10) & value > 0,
                    "led": (0x20) & value > 0,
                    "sleep_mode": (0x80) & value > 0,
                    "speed": (0x07) & value,
                    "timer_hours": round((0x0F0000 & value) / 65536, 0),
                    "timer_time_elapsed_mins": round(
                        (0xFF000000 & value) * 4 / 16777216, 0
                    ),
                }
            )

        self._device.async_update_state({**state, "is_online": True})
        self._device.async_update_last_seen(utcnow().timestamp())
        self.update_ha_state_if_required()

    def update_ha_state_if_required(self):
        """Update entity state on HA if required."""
        if self.device_state != self._device.state:
            self._attr_device_state = self._device.state
            self.async_schedule_update_ha_state()

    def _refresh_availability(self, now: datetime):
        """Update is_online state based on last_seen."""
        if self._device.last_seen:
            _LOGGER.debug(
                "Refreshing availability of %s (%s) - (%s)",
                self._device.name,
                self._device.id,
                self.name,
            )
            self._device.async_update_state(
                {
                    "is_online": now.timestamp() - self._device.last_seen
                    <= AVAILABILITY_TIMEOUT
                }
            )
            self.update_ha_state_if_required()
