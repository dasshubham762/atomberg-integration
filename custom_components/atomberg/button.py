"""Button platform for Atomberg integration."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_CONTROL_METHOD, ControlMethod
from .device import AtombergPurifier
from .ir_button import async_setup_entry as ir_async_setup_entry
from .purifier_coordinator import AtombergPurifierCoordinator
from .purifier_entity import AtombergPurifierEntity, purifier_async_setup_entry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Atomberg button entities from a config entry."""
    if entry.data.get(CONF_CONTROL_METHOD) == ControlMethod.IR:
        await ir_async_setup_entry(hass, entry, async_add_entities)
        return

    await purifier_async_setup_entry(
        hass,
        entry,
        async_add_entities,
        lambda coordinator, device: [PurifierRefreshButton(coordinator, device)],
    )


class PurifierRefreshButton(AtombergPurifierEntity, ButtonEntity):
    """Refresh water purifier state from the cloud. Uses one API call."""

    _attr_icon = "mdi:refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: AtombergPurifierCoordinator, device: AtombergPurifier
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, device, Platform.BUTTON, "refresh", "refresh")

    @property
    def available(self) -> bool:
        """Keep refresh available to recover from failed updates."""
        return True

    async def async_press(self) -> None:
        """Refresh purifier states."""
        await self.coordinator.async_request_refresh()
