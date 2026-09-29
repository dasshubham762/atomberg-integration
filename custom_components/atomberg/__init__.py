"""The Atomberg integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady

from .api import AtombergCloudAPI
from .const import (
    CONF_CONTROL_METHOD,
    CONF_POLLING_INTERVAL,
    CONF_REFRESH_TOKEN,
    CONF_STATE_UPDATE_METHOD,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_STATE_UPDATE_METHOD,
    DOMAIN,
    ENTRIES,
    UDP_LISTENER,
    ControlMethod,
    StateUpdateMethod,
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

    state_update_method = entry.options.get(
        CONF_STATE_UPDATE_METHOD, DEFAULT_STATE_UPDATE_METHOD
    )
    use_polling = state_update_method == StateUpdateMethod.POLLING
    polling_interval = entry.options.get(
        CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
    )

    # Reload the entry when its options change so switching between broadcast and
    # polling (and interval changes) take effect without restarting Home Assistant.
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    api = AtombergCloudAPI(
        hass, entry.data[CONF_API_KEY], entry.data[CONF_REFRESH_TOKEN]
    )

    try:
        await api.test_connection()
    except Exception as e:
        raise ConfigEntryNotReady("Failed to initialize Atomberg integration.") from e

    # The shared UDP listener is only needed when refreshing state from broadcasts.
    udp_listener = None
    if not use_polling:
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
        use_polling=use_polling,
        polling_interval=polling_interval,
    )

    # Fetch the initial state up front so entities aren't stuck unavailable.
    if use_polling:
        await coordinator.async_config_entry_first_refresh()

    domain_data[ENTRIES][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, CLOUD_PLATFORMS)

    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when its options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


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
    udp_listener: UDPListener | None = domain_data[UDP_LISTENER]

    unload_ok = await hass.config_entries.async_unload_platforms(entry, CLOUD_PLATFORMS)
    if not unload_ok:
        return False

    domain_data[ENTRIES].pop(entry.entry_id, None)

    # The UDP listener is absent when every cloud entry uses polling.
    if udp_listener is not None:
        udp_listener.remove_callback(entry)

        if not domain_data[ENTRIES]:
            udp_listener.close()
            domain_data[UDP_LISTENER] = None

    return unload_ok
