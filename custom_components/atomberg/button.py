"""Button platform for Atomberg integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_CONTROL_METHOD, ControlMethod


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Atomberg button entities from a config entry."""
    if entry.data.get(CONF_CONTROL_METHOD) == ControlMethod.IR:
        from .ir_button import async_setup_entry as ir_async_setup_entry

        await ir_async_setup_entry(hass, entry, async_add_entities)
    # Cloud control has no button entities — nothing to set up.
