"""Support for switch entities of Atomberg integration."""

from logging import getLogger
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AtombergDataUpdateCoordinator
from .device import (
    ATTR_IDLE_SLEEP,
    ATTR_SLEEP,
    ATTR_SLEEP_MODE,
    AtombergDevice,
    AtombergPurifier,
)
from .entity import AtombergEntity, platform_async_setup_entry
from .purifier_coordinator import AtombergPurifierCoordinator
from .purifier_entity import AtombergPurifierEntity, purifier_async_setup_entry

_LOGGER = getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Automatically setup the switch entities from the devices list."""
    await platform_async_setup_entry(
        hass, entry, async_add_entities, AtombergSleepModeSwitchEntity
    )
    await purifier_async_setup_entry(
        hass,
        entry,
        async_add_entities,
        lambda coordinator, device: [
            entity_type(coordinator, device)
            for entity_type in (PurifierIdleSleepSwitch, PurifierSleepWindowSwitch)
            if device.supports(entity_type.key)
        ],
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


class PurifierIdleSleepSwitch(AtombergPurifierEntity, SwitchEntity):
    """Water purifier display sleep while idle switch entity."""

    key = ATTR_IDLE_SLEEP
    _attr_icon = "mdi:monitor-off"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: AtombergPurifierCoordinator, device: AtombergPurifier
    ) -> None:
        """Init idle sleep entity."""
        super().__init__(
            coordinator, device, Platform.SWITCH, self.key, "idle display sleep"
        )

    @property
    def is_on(self) -> bool | None:
        """Whether idle sleep is on."""
        if (value := self.device_state.get(self.key)) is None:
            return None
        return bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on entity."""
        await self._device.async_set_idle_sleep(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off entity."""
        await self._device.async_set_idle_sleep(False)
        self.async_write_ha_state()


class PurifierSleepWindowSwitch(PurifierIdleSleepSwitch):
    """Water purifier daily sleep window switch entity."""

    key = ATTR_SLEEP_MODE
    _attr_icon = "mdi:sleep"

    def __init__(
        self, coordinator: AtombergPurifierCoordinator, device: AtombergPurifier
    ) -> None:
        """Init sleep window entity."""
        super().__init__(coordinator, device)
        self._attr_name = f"{self._device.name} sleep window"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on entity."""
        await self._device.async_set_sleep_window(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off entity."""
        await self._device.async_set_sleep_window(False)
        self.async_write_ha_state()
