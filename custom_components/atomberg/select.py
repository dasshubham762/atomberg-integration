"""Support for select entities of Atomberg integration."""

from logging import getLogger

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AtombergDataUpdateCoordinator
from .device import ATTR_TIMER_HOURS, TIMER_MAPPING, AtombergDevice
from .entity import AtombergEntity, platform_async_setup_entry

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
