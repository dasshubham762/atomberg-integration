"""Support for Atomberg Fans."""

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import DOMAIN, SUPPORTED_FAN_SERIES
from .coordinator import AtombergDataUpdateCoordinator
from .device import AtombergDevice
from .entity import AtombergEntity

ORDERED_FAN_SPEEDS = range(1, 7)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Automatically setup the fans from the devices list."""
    coordinator: AtombergDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    api = coordinator.api
    async_add_entities(
        AtombergFanEntity(coordinator, device)
        for device in filter(
            lambda d: d.series in SUPPORTED_FAN_SERIES, api.device_list.values()
        )
    )


class AtombergFanEntity(AtombergEntity, FanEntity):
    """Atomberg Fan."""

    _attr_supported_features = FanEntityFeature.SET_SPEED

    def __init__(
        self,
        coordinator: AtombergDataUpdateCoordinator,
        device: AtombergDevice,
    ) -> None:
        """Init Atomberg Fan."""
        super().__init__(coordinator, device)

        self._attr_unique_id = self._get_unique_id(Platform.FAN)
        self._attr_name = self._device.name

    @property
    def is_on(self) -> bool:
        """Whether the fan is on."""
        return self.device_state["power"]

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return len(ORDERED_FAN_SPEEDS)

    @property
    def percentage(self) -> int:
        """Get fan speed in percentage."""
        return ordered_list_item_to_percentage(
            ORDERED_FAN_SPEEDS,
            self.device_state.get("speed", ORDERED_FAN_SPEEDS[0]),
        )

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self._device.async_turn_off()
        else:
            await self._device.async_set_speed(
                percentage_to_ordered_list_item(
                    ORDERED_FAN_SPEEDS, percentage=percentage
                )
            )

    async def async_turn_on(self, *args, **kwargs: Any) -> None:
        """Turn on the entity."""
        await self._device.async_turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the entity."""
        await self._device.async_turn_off()
