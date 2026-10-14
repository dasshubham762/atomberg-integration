"""Support for select entities of Atomberg integration."""

from logging import getLogger

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AtombergDataUpdateCoordinator
from .device import (
    ATTR_FALLBACK_MODE,
    ATTR_MODE,
    ATTR_TIMER_HOURS,
    PURIFIER_FALLBACK_MODES,
    PURIFIER_MODES,
    TIMER_MAPPING,
    AtombergDevice,
    AtombergPurifier,
)
from .entity import AtombergEntity, platform_async_setup_entry
from .purifier_coordinator import AtombergPurifierCoordinator
from .purifier_entity import AtombergPurifierEntity, purifier_async_setup_entry

_LOGGER = getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Automatically setup the select entities from the devices list."""
    await platform_async_setup_entry(
        hass,
        entry,
        async_add_entities,
        SetTimerSelect,
    )
    await purifier_async_setup_entry(
        hass,
        entry,
        async_add_entities,
        lambda coordinator, device: [
            PurifierModeSelect(coordinator, device),
            *(
                [PurifierFallbackModeSelect(coordinator, device)]
                if device.supports(ATTR_FALLBACK_MODE)
                else []
            ),
        ],
    )


class SetTimerSelect(AtombergEntity, SelectEntity):
    """Set timer select entity."""

    def __init__(
        self, coordinator: AtombergDataUpdateCoordinator, device: AtombergDevice
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, device, _LOGGER)

        self._attr_unique_id = self._get_unique_id(Platform.SELECT, suffix="set_timer")
        self._attr_name = self._device.name + " set timer"
        self._attr_icon = "mdi:av-timer"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def options(self) -> list[str]:
        """Get the available options."""
        return [_t[1] for _t in TIMER_MAPPING]

    @property
    def current_option(self) -> str:
        """Get the current option."""
        return next(
            filter(
                lambda _t: _t[0] == self.device_state[ATTR_TIMER_HOURS],
                TIMER_MAPPING,
            )
        )[1]

    async def async_select_option(self, option: str) -> None:
        """When selected an option."""
        await self._device.async_set_timer(self.options.index(option))


class PurifierModeSelect(AtombergPurifierEntity, SelectEntity):
    """Water purifier purification mode select entity."""

    _attr_icon = "mdi:water-check"
    _modes = PURIFIER_MODES
    _key = ATTR_MODE

    def __init__(
        self, coordinator: AtombergPurifierCoordinator, device: AtombergPurifier
    ) -> None:
        """Initialize the entity."""
        super().__init__(
            coordinator, device, Platform.SELECT, self._key, "purification mode"
        )
        self._attr_options = list(self._modes.values())

    @property
    def current_option(self) -> str | None:
        """Get the current option."""
        return self._modes.get(self.device_state.get(self._key))

    async def async_select_option(self, option: str) -> None:
        """When selected an option."""
        value = next(k for k, v in self._modes.items() if v == option)
        await self._async_set_value(value)
        self.async_write_ha_state()

    async def _async_set_value(self, value: int) -> None:
        await self._device.async_set_mode(value)


class PurifierFallbackModeSelect(PurifierModeSelect):
    """Water purifier fallback mode select entity."""

    _attr_icon = "mdi:water-sync"
    _attr_entity_category = EntityCategory.CONFIG
    _modes = PURIFIER_FALLBACK_MODES
    _key = ATTR_FALLBACK_MODE

    def __init__(
        self, coordinator: AtombergPurifierCoordinator, device: AtombergPurifier
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, device)
        self._attr_name = f"{self._device.name} fallback mode"

    async def _async_set_value(self, value: int) -> None:
        await self._device.async_set_fallback_mode(value)
