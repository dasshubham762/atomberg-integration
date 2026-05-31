"""The Atomberg integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY, ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady

from .api import AtombergCloudAPI
from .const import (
    CONF_CONTROL_METHOD,
    CONF_DEVICE_ID,
    CONF_DEVICE_SERIES,
    CONF_IP_ADDRESS,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    ENTRIES,
    SETUP_ACTIVE,
    UDP_LISTENER,
    ControlMethod,
)
from .coordinator import AtombergDataUpdateCoordinator
from .udp_listener import DISCOVERY_CALLBACK_KEY, UDPListener

_LOGGER = logging.getLogger(__name__)

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

LOCAL_UDP_PLATFORMS: list[Platform] = [
    Platform.FAN,
    Platform.SWITCH,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SELECT,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Atomberg integration domain.

    Runs before any config entries are loaded.  Starts the shared UDP listener
    early so that device broadcasts can trigger automatic discovery flows even
    when no entries exist yet.
    """
    domain_data = hass.data.setdefault(DOMAIN, {UDP_LISTENER: None, ENTRIES: {}})

    udp_listener = UDPListener(hass)
    try:
        await udp_listener.start()
    except Exception:
        _LOGGER.warning(
            "Atomberg: failed to start UDP listener during integration setup; "
            "local discovery will not be available until an entry is configured."
        )
        return True

    domain_data[UDP_LISTENER] = udp_listener
    domain_data[SETUP_ACTIVE] = True

    def _discovery_callback(msg_data: dict) -> None:
        """Fire an integration-discovery flow for previously-unknown devices."""
        device_id = msg_data.get("device_id")
        if not device_id:
            return

        # Skip if this device is already managed by an existing local entry.
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.data.get(CONF_DEVICE_ID) == device_id:
                return

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_INTEGRATION_DISCOVERY},
                data={
                    CONF_DEVICE_ID: device_id,
                    CONF_DEVICE_SERIES: msg_data.get("device_series"),
                    CONF_IP_ADDRESS: msg_data.get("ip_address"),
                },
            )
        )

    udp_listener.add_callback(DISCOVERY_CALLBACK_KEY, _discovery_callback)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Atomberg from a config entry."""
    control_method = entry.data.get(CONF_CONTROL_METHOD, ControlMethod.CLOUD)

    if control_method == ControlMethod.IR:
        return await _async_setup_ir_entry(hass, entry)

    if control_method == ControlMethod.LOCAL_DISCOVERY:
        return await _async_setup_local_discovery_entry(hass, entry)

    if control_method == ControlMethod.LOCAL_UDP:
        return await _async_setup_local_udp_entry(hass, entry)

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
        hass=hass,
        api=api,
        udp_listener=udp_listener,
        config_entry=entry,
    )
    domain_data[ENTRIES][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, CLOUD_PLATFORMS)

    return True


async def _async_setup_local_udp_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Atomberg using local UDP control (no cloud credentials required)."""
    domain_data = hass.data.setdefault(DOMAIN, {UDP_LISTENER: None, ENTRIES: {}})

    # Listener is normally already running from async_setup; start as fallback.
    if not domain_data[UDP_LISTENER]:
        udp_listener = UDPListener(hass)
        try:
            await udp_listener.start()
        except Exception:
            raise ConfigEntryError("Failed to start UDP listener.")  # noqa: B904
        domain_data[UDP_LISTENER] = udp_listener
    else:
        udp_listener = domain_data[UDP_LISTENER]

    coordinator = AtombergDataUpdateCoordinator(
        hass=hass,
        api=None,
        udp_listener=udp_listener,
        config_entry=entry,
    )
    domain_data[ENTRIES][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, LOCAL_UDP_PLATFORMS)

    # Trigger an initial no-op local command to prompt a fresh state broadcast.
    # If IP is not known yet, this will no-op and state will update on next push.
    if coordinator.devices:
        await coordinator.devices[0].async_request_state_refresh()

    return True


async def _async_setup_local_discovery_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up Atomberg local discovery bootstrap entry."""
    # Discovery is handled globally via async_setup(); this entry only exists
    # to let the user opt into local autodiscovery from the UI.
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

    if control_method == ControlMethod.LOCAL_DISCOVERY:
        return True

    platforms = (
        LOCAL_UDP_PLATFORMS
        if control_method == ControlMethod.LOCAL_UDP
        else CLOUD_PLATFORMS
    )

    domain_data = hass.data[DOMAIN]
    udp_listener: UDPListener = domain_data[UDP_LISTENER]

    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if not unload_ok:
        return False

    domain_data[ENTRIES].pop(entry.entry_id, None)
    udp_listener.remove_callback(entry)

    # Only close the listener when async_setup did NOT own it and no entries remain.
    if not domain_data.get(SETUP_ACTIVE, False) and not domain_data[ENTRIES]:
        udp_listener.close()
        domain_data[UDP_LISTENER] = None

    return unload_ok
