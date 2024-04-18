"""The Atomberg integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady

from .api import AtombergCloudAPI
from .const import CONF_REFRESH_TOKEN, DOMAIN
from .coordinator import AtombergDataUpdateCoordinator
from .udp_listener import UDPListener

PLATFORMS: list[Platform] = [Platform.FAN, Platform.SWITCH, Platform.LIGHT]


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

    udp_listener = UDPListener(hass)
    coordinator = AtombergDataUpdateCoordinator(
        hass=hass, api=api, udp_listener=udp_listener
    )
    hass.data[DOMAIN][entry.entry_id] = coordinator

    try:
        await udp_listener.start()
    except Exception:
        raise ConfigEntryError("Failed to start udp listener.")  # noqa: B904

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: AtombergDataUpdateCoordinator = hass.data[DOMAIN].pop(
            entry.entry_id
        )
        coordinator.udp_listener.close()

    return unload_ok
