"""Support for extra features of Atomberg Fan."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SUPPORTED_BINARY_LED_SERIES
from .coordinator import AtombergDataUpdateCoordinator
from .device import AtombergDevice
from .entity import AtombergEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Automatically setup the fan lights from the devices list."""
    coordinator: AtombergDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    api = coordinator.api

    # Add binary LED switch entities
    async_add_entities(
        AtombergFanLightSwitchEntity(coordinator, device)
        for device in filter(
            lambda d: d.series in SUPPORTED_BINARY_LED_SERIES, api.device_list.values()
        )
    )

    # Add binary sleep mode switch entities
    async_add_entities(
        AtombergSleepModeSwitchEntity(coordinator, device)
        for device in api.device_list.values()
    )


class AtombergFanLightSwitchEntity(AtombergEntity, SwitchEntity):
    """Light entity for atomberg Fan."""

    def __init__(
        self, coordinator: AtombergDataUpdateCoordinator, device: AtombergDevice
    ) -> None:
        """Init Light entity."""
        super().__init__(coordinator, device)

        self._attr_name = self._device.name + " LED"
        self._attr_unique_id = self._get_unique_id(Platform.SWITCH, "led")

    @property
    def is_on(self) -> bool:
        """Whether the fan LED is on."""
        return self._device.state["led"]

    @property
    def icon(self) -> str | None:
        """Get dynamic icon."""
        return "mdi:led-variant-on" if self.is_on else "mdi:led-variant-off"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on entity."""
        await self._device.async_turn_on_light()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off entity."""
        await self._device.async_turn_off_light()


class AtombergSleepModeSwitchEntity(AtombergEntity, SwitchEntity):
    """Sleep mode entity for atomberg Fan."""

    def __init__(
        self, coordinator: AtombergDataUpdateCoordinator, device: AtombergDevice
    ) -> None:
        """Init sleep mode entity."""
        super().__init__(coordinator, device)

        self._attr_name = self._device.name + " sleep mode"
        self._attr_unique_id = self._get_unique_id(Platform.SWITCH, "sleep_mode")

    @property
    def is_on(self) -> bool:
        """Whether the fan sleep mode is on."""
        return self._device.state["sleep_mode"]

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
