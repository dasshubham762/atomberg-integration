"""The Atomberg integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady

from .api import AtombergCloudAPI
from .const import (
    CONF_CONTROL_METHOD,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    ENTRIES,
    UDP_LISTENER,
    ControlMethod,
)
from .coordinator import AtombergDataUpdateCoordinator
from .udp_listener import UDPListener

CLOUD_PLATFORMS: list[Platform] = [
    Platform.FAN,
    Platform.SWITCH,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SELECT,
]

IR_PLATFORMS: list[Platform] = [
    Platform.FAN,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Atomberg from a config entry."""
    control_method = entry.data.get(CONF_CONTROL_METHOD, ControlMethod.CLOUD)

    if control_method == ControlMethod.IR:
        return await _async_setup_ir_entry(hass, entry)

    return await _async_setup_cloud_entry(hass, entry)


async def _async_setup_cloud_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Atomberg using cloud API."""
    domain_data = hass.data.setdefault(DOMAIN, {UDP_LISTENER: None, ENTRIES: {}})

    api = AtombergCloudAPI(
        hass, entry.data[CONF_API_KEY], entry.data[CONF_REFRESH_TOKEN]
    )

    try:
        await api.test_connection()
    except Exception as e:
        raise ConfigEntryNotReady("Failed to initialize Atomberg integration.") from e

    if not domain_data[UDP_LISTENER]:
        udp_listener = UDPListener(hass)
        domain_data[UDP_LISTENER] = udp_listener

        try:
            await udp_listener.start()
        except Exception:
            raise ConfigEntryError("Failed to start udp listener.")  # noqa: B904
    else:
        udp_listener = domain_data[UDP_LISTENER]

    coordinator = AtombergDataUpdateCoordinator(
        hass=hass, api=api, udp_listener=udp_listener
    )
    domain_data[ENTRIES][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, CLOUD_PLATFORMS)

    return True


async def _async_setup_ir_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Atomberg using IR control."""
    await hass.config_entries.async_forward_entry_setups(entry, IR_PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    control_method = entry.data.get(CONF_CONTROL_METHOD, ControlMethod.CLOUD)

    if control_method == ControlMethod.IR:
        return await hass.config_entries.async_unload_platforms(entry, IR_PLATFORMS)

    domain_data = hass.data[DOMAIN]
    udp_listener: UDPListener = domain_data[UDP_LISTENER]

    unload_ok = await hass.config_entries.async_unload_platforms(entry, CLOUD_PLATFORMS)
    if not unload_ok:
        return False

    domain_data[ENTRIES].pop(entry.entry_id, None)

    udp_listener.remove_callback(entry)

    if not domain_data[ENTRIES]:
        udp_listener.close()
        domain_data[UDP_LISTENER] = None

    return unload_ok
