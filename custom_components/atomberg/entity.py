"""Base Atomberg entity."""

from datetime import datetime, timedelta
from logging import Logger
from typing import TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.dt import utcnow

from .const import DOMAIN, MANUFACTURER
from .coordinator import AtombergDataUpdateCoordinator
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
    LIGHT_MODE_COOL,
    LIGHT_MODE_DAYLIGHT,
    LIGHT_MODE_WARM,
    AtombergDevice,
)

AVAILABILITY_TIMEOUT = 15  # Seconds

_EntityT = TypeVar("_EntityT", bound="AtombergEntity")


async def platform_async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    entity_type: _EntityT,
) -> None:
    """Set up an Atomberg platform."""
    coordinator: AtombergDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        entity_type(coordinator=coordinator, device=device)
        for device in coordinator.get_devices()
    )


class AtombergEntity(CoordinatorEntity, Entity):
    """Atomberg base entity."""

    def __init__(
        self,
        coordinator: AtombergDataUpdateCoordinator,
        device: AtombergDevice,
        logger: Logger,
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
        self._logger = logger
        self._stop_availability_refresher = None

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
        return self.device_state[ATTR_IS_ONLINE]

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
            value = state_string.split(",")[0].strip()
            if not value.isnumeric():
                return
            value = int(value)

            state.update(
                {
                    ATTR_POWER: (0x10) & value > 0,
                    ATTR_LED: (0x20) & value > 0,
                    ATTR_SLEEP: (0x80) & value > 0,
                    ATTR_SPEED: (0x07) & value,
                    ATTR_TIMER_HOURS: round((0x0F0000 & value) >> 16),
                    ATTR_TIMER_TIME_ELAPSED_MINS: round(
                        (0xFF000000 & value) >> (24 - 2)
                    ),
                }
            )

            # Set brightness value if device supports brightness control
            if self._device.supports_brightness_control:
                state[ATTR_BRIGHTNESS] = round(((0x7F00) & value) >> 8)

            # Set color mode if device supports color modes
            if self._device.supports_color_effect:
                cool = ((0x08) & value) > 0
                warm = ((0x8000) & value) > 0

                if cool and warm:
                    light_mode = LIGHT_MODE_DAYLIGHT
                elif cool:
                    light_mode = LIGHT_MODE_COOL
                elif warm:
                    light_mode = LIGHT_MODE_WARM

                state[ATTR_LIGHT_MODE] = light_mode

        self._device.update_state({**state, ATTR_IS_ONLINE: True})
        self._device.update_last_seen(utcnow().timestamp())
        self.update_ha_state_if_required()

    def update_ha_state_if_required(self):
        """Update entity state on HA if required."""
        if self.device_state != self._device.state:
            self._attr_device_state = self._device.state
            self.async_schedule_update_ha_state()

    @callback
    def _refresh_availability(self, now: datetime):
        """Update is_online state based on last_seen."""
        if self._device.last_seen and self.available:
            self._logger.debug(
                "Refreshing availability of %s (%s) - (%s)",
                self._device.name,
                self._device.id,
                self.name,
            )
            self._device.update_state(
                {
                    ATTR_IS_ONLINE: now.timestamp() - self._device.last_seen
                    <= AVAILABILITY_TIMEOUT
                }
            )
            self.update_ha_state_if_required()

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()

        # Start availability refresher
        self._stop_availability_refresher = async_track_time_interval(
            self.hass, self._refresh_availability, timedelta(seconds=30)
        )

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        # Stop availability refresher
        if self._stop_availability_refresher:
            self._stop_availability_refresher()
            self._stop_availability_refresher = None
