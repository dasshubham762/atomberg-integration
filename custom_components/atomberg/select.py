"""Support for select entities of Atomberg integration."""

from logging import getLogger

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AtombergDataUpdateCoordinator
from .device import ATTR_SPEED, ATTR_TIMER_HOURS, TIMER_MAPPING, AtombergDevice
from .entity import AtombergEntity, platform_async_setup_entry

_LOGGER = getLogger(__name__)

SPEED_OPTIONS = ["1", "2", "3", "4", "5", "6"]


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
    await platform_async_setup_entry(
        hass,
        entry,
        async_add_entities,
        SetSpeedSelect,
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
                lambda _t: _t[0] == self.device_state.get(ATTR_TIMER_HOURS, 0),
                TIMER_MAPPING,
            ),
            TIMER_MAPPING[0],
        )[1]

    async def async_select_option(self, option: str) -> None:
        """When selected an option."""
        await self._device.async_set_timer(self.options.index(option))


class SetSpeedSelect(AtombergEntity, SelectEntity):
    """Set speed select entity for discrete 1-6 speed control."""

    def __init__(
        self, coordinator: AtombergDataUpdateCoordinator, device: AtombergDevice
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, device, _LOGGER)

        self._attr_unique_id = self._get_unique_id(Platform.SELECT, suffix="set_speed")
        self._attr_name = self._device.name + " set speed"
        self._attr_icon = "mdi:fan-speed-1"

    @property
    def options(self) -> list[str]:
        """Get the available speed options (1 to 6)."""
        return SPEED_OPTIONS

    @property
    def current_option(self) -> str:
        """Get current speed option."""
        speed = self.device_state.get(ATTR_SPEED, 1)
        return str(speed) if str(speed) in SPEED_OPTIONS else SPEED_OPTIONS[0]

    async def async_select_option(self, option: str) -> None:
        """Set fan speed directly."""
        try:
            await self._device.async_set_speed(int(option))
        except (ValueError, TypeError) as err:
            _LOGGER.error("Failed to set speed option %s: %s", option, err)
