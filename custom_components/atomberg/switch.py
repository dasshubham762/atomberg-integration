"""Support for switch entities of Atomberg integration."""

from logging import getLogger
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AtombergDataUpdateCoordinator
from .device import ATTR_SLEEP, AtombergDevice
from .entity import AtombergEntity

_LOGGER = getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Automatically setup the switch entities from the devices list."""
    coordinator: AtombergDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    api = coordinator.api

    # Add binary sleep mode switch entities
    async_add_entities(
        AtombergSleepModeSwitchEntity(coordinator, device)
        for device in api.device_list.values()
    )


class AtombergSleepModeSwitchEntity(AtombergEntity, SwitchEntity):
    """Sleep mode entity for atomberg Fan."""

    def __init__(
        self, coordinator: AtombergDataUpdateCoordinator, device: AtombergDevice
    ) -> None:
        """Init sleep mode entity."""
        super().__init__(coordinator, device, _LOGGER)

        self._attr_name = self._device.name + " sleep mode"
        self._attr_unique_id = self._get_unique_id(Platform.SWITCH, ATTR_SLEEP)
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        """Whether the fan sleep mode is on."""
        return self.device_state[ATTR_SLEEP]

    @property
    def icon(self) -> str | None:
        """Get dynamic icon."""
        return "mdi:sleep" if self.is_on else "mdi:sleep-off"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on entity."""
        await self._device.async_turn_on_sleep_mode()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off entity."""
        await self._device.async_turn_off_sleep_mode()
