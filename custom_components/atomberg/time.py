"""Support for time entities of Atomberg integration."""

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device import ATTR_SLEEP_MODE, ATTR_START_UTC, ATTR_STOP_UTC, AtombergPurifier
from .purifier_coordinator import AtombergPurifierCoordinator
from .purifier_entity import AtombergPurifierEntity, purifier_async_setup_entry


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Automatically setup the time entities from the devices list."""
    await purifier_async_setup_entry(
        hass,
        entry,
        async_add_entities,
        lambda coordinator, device: (
            [
                PurifierSleepWindowTime(coordinator, device, ATTR_START_UTC, "start"),
                PurifierSleepWindowTime(coordinator, device, ATTR_STOP_UTC, "end"),
            ]
            if device.supports(ATTR_SLEEP_MODE)
            else []
        ),
    )


class PurifierSleepWindowTime(AtombergPurifierEntity, TimeEntity):
    """Water purifier daily sleep window start or end time."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: AtombergPurifierCoordinator,
        device: AtombergPurifier,
        key: str,
        name: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(
            coordinator, device, Platform.TIME, key, f"sleep window {name}"
        )
        self._key = key
        self._attr_icon = (
            "mdi:clock-start" if key == ATTR_START_UTC else "mdi:clock-end"
        )

    @property
    def native_value(self) -> time | None:
        """Get the time in local time zone."""
        start, stop = self._device.sleep_window
        return start if self._key == ATTR_START_UTC else stop

    async def async_set_value(self, value: time) -> None:
        """Set the time. Sent right away only if the sleep window is on."""
        await self._device.async_set_sleep_window_time(self._key, value)
        self.async_write_ha_state()
