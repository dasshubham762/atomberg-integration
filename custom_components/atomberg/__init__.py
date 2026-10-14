"""The Atomberg integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady

from .api import DEVICE_TYPE_WATER_PURIFIER, AtombergCloudAPI
from .const import (
    CONF_CONTROL_METHOD,
    CONF_PURIFIER_POLL_INTERVAL,
    CONF_REFRESH_TOKEN,
    DEFAULT_PURIFIER_POLL_INTERVAL,
    DOMAIN,
    ENTRIES,
    PURIFIER_COORDINATORS,
    UDP_LISTENER,
    ControlMethod,
)
from .coordinator import AtombergDataUpdateCoordinator
from .device import AtombergPurifier
from .purifier_coordinator import AtombergPurifierCoordinator
from .udp_listener import UDPListener

CLOUD_PLATFORMS: list[Platform] = [
    Platform.FAN,
    Platform.SWITCH,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.TIME,
    Platform.BINARY_SENSOR,
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

    purifiers = [
        AtombergPurifier(data=data, api=api)
        for data in api.device_list.values()
        if data["device_type"] == DEVICE_TYPE_WATER_PURIFIER
    ]
    if purifiers:
        purifier_coordinator = AtombergPurifierCoordinator(
            hass,
            entry,
            api,
            purifiers,
            entry.options.get(
                CONF_PURIFIER_POLL_INTERVAL, DEFAULT_PURIFIER_POLL_INTERVAL
            ),
        )
        # Seed with the state fetched during device sync to save an API call
        purifier_coordinator.async_set_updated_data({d.id: d.state for d in purifiers})
        domain_data.setdefault(PURIFIER_COORDINATORS, {})[entry.entry_id] = (
            purifier_coordinator
        )
        entry.async_on_unload(entry.add_update_listener(_async_update_options))

    await hass.config_entries.async_forward_entry_setups(entry, CLOUD_PLATFORMS)

    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply updated options to the purifier coordinator."""
    coordinator: AtombergPurifierCoordinator | None = (
        hass.data[DOMAIN].get(PURIFIER_COORDINATORS, {}).get(entry.entry_id)
    )
    if coordinator:
        coordinator.update_interval = timedelta(
            minutes=entry.options.get(
                CONF_PURIFIER_POLL_INTERVAL, DEFAULT_PURIFIER_POLL_INTERVAL
            )
        )


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
    domain_data.get(PURIFIER_COORDINATORS, {}).pop(entry.entry_id, None)

    udp_listener.remove_callback(entry)

    if not domain_data[ENTRIES]:
        udp_listener.close()
        domain_data[UDP_LISTENER] = None

    return unload_ok
