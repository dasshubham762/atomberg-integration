"""The Atomberg integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import AtombergCloudAPI
from .const import CONF_REFRESH_TOKEN, DOMAIN
from .coordinator import AtombergDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.FAN, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Atomberg from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    api = AtombergCloudAPI(
        hass, entry.data[CONF_API_KEY], entry.data[CONF_REFRESH_TOKEN]
    )

    # Test API connection
    status = await api.test_connection()
    if not status:
        raise ConfigEntryNotReady("Failed to initialize Atomberg integration.")

    coordinator = AtombergDataUpdateCoordinator(hass=hass, api=api)
    await coordinator.api.async_sync_list_of_devices()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
