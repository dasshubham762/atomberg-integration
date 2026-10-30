"""Device wrapper for Atomberg fans (cloud and local UDP modes)."""

import json
import socket
from copy import deepcopy
from datetime import UTC, datetime, time, timedelta
from logging import getLogger
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import format_mac
from homeassistant.util import dt as dt_util

from .api import AtombergCloudAPI
from .const import CONF_USE_CLOUD_CONTROL, UNKNOWN_SERIES

_LOGGER = getLogger(__name__)

SUPPORTED_BRIGHTNESS_CONTROL_SERIES = ["I1", "I5", "M1", "S1", "S2"]
SUPPORTED_COLOR_EFFECT_SERIES = ["I1", "I5"]

ATTR_IS_ONLINE = "is_online"
ATTR_POWER = "power"
ATTR_SPEED = "speed"
ATTR_SLEEP = "sleep"
ATTR_LIGHT_MODE = "light_mode"
ATTR_LED = "led"
ATTR_TIMER_HOURS = "timer_hours"
ATTR_TIMER_TIME_ELAPSED_MINS = "timer_time_elapsed_mins"
LIGHT_MODE_DAYLIGHT = "daylight"
LIGHT_MODE_COOL = "cool"
LIGHT_MODE_WARM = "warm"
LED_BRIGHTNESS_SCALE = (1, 100)
TIMER_MAPPING = [
    (0, "Off"),
    (1, "1 hour"),
    (2, "2 hours"),
    (3, "3 hours"),
    (6, "6 hours"),
]

# Water purifier
ATTR_MODE = "mode"
ATTR_FALLBACK_MODE = "fallback_mode"
ATTR_TDS_THRESHOLD = "tds_threshold"
ATTR_IDLE_SLEEP = "idle_sleep"
ATTR_SLEEP_MODE = "sleep_mode"
ATTR_START_UTC = "start_utc"
ATTR_STOP_UTC = "stop_utc"
ATTR_INPUT_TDS = "input_tds"
ATTR_TANK_TDS = "tank_tds"
ATTR_CHOKING_FAULTS = "choking_faults"
ATTR_SYSTEM_FAULTS = "system_faults"
ATTR_TS_EPOCH_SECONDS = "ts_epoch_seconds"
PURIFIER_MODES = {
    0: "RO only",
    1: "Adaptive",
    2: "TasteTune 50-100 ppm",
    3: "TasteTune 75-125 ppm",
    4: "TasteTune 100-150 ppm",
    10: "Vacation",
}
PURIFIER_FALLBACK_MODES = {k: PURIFIER_MODES[k] for k in (0, 2, 3, 4)}
TDS_THRESHOLD_RANGE = (100, 300)


class AtombergDevice:
    """Atomberg device."""

    def __init__(
        self,
        data: dict[str, Any],
        api: AtombergCloudAPI | None,
        config_entry: ConfigEntry = None,
    ) -> None:
        """Init Atomberg device."""
        self._device_id = data["device_id"]
        self._color = data.get("color")
        self._series = data.get("series", UNKNOWN_SERIES)
        self._model = data.get("model", "Atomberg Fan")
        self._name = data["name"]
        self._api = api
        self._state: dict = data.get("state", {})
        self._last_seen: int = None
        # Cloud devices start with an authoritative state; local ones only have
        # placeholder defaults, so a restored state may fill those in.
        self._state_confirmed = api is not None and bool(self._state)
        self._ip_addr: str = data.get("ip_address")
        self._options = config_entry.options if config_entry else {}

        # Add options update listener
        if config_entry:
            config_entry.async_on_unload(
                config_entry.add_update_listener(self._update_options)
            )

    @property
    def supports_brightness_control(self):
        """Check whether device supports brightness control."""
        return self._series in SUPPORTED_BRIGHTNESS_CONTROL_SERIES

    @property
    def supports_color_effect(self):
        """Check whether device supports color modes."""
        return self._series in SUPPORTED_COLOR_EFFECT_SERIES

    @property
    def state(self) -> dict[str, Any]:
        """Get state."""
        return deepcopy(self._state)

    @property
    def name(self) -> str:
        """Get name."""
        return self._name

    @property
    def id(self) -> str:
        """Get device_id."""
        return self._device_id

    @property
    def color(self) -> str:
        """Get color."""
        return self._color

    @property
    def series(self) -> str:
        """Get series."""
        return self._series

    @property
    def model(self) -> str:
        """Get model."""
        return self._model

    @property
    def last_seen(self) -> float:
        """Get last seen UTC timestamp."""
        return self._last_seen

    @property
    def ip_address(self) -> str | None:
        """Get IP address."""
        return self._ip_addr

    @property
    def mac(self) -> str:
        """Get MAC address."""
        return format_mac(self.id)

    def update_last_seen(self, value: float):
        """Update last seen timestamp."""
        self._last_seen = value

    def update_ip_address(self, value: str):
        """Update IP address."""
        if self._ip_addr != value:
            _LOGGER.debug("IP address updated for %s: %s", self.name, value)
            self._ip_addr = value

    async def _update_options(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Update options."""
        self._options = config_entry.options
        _LOGGER.debug("Options updated for %s: %s", self.name, self._options)

    async def _async_send_command(self, command: dict) -> bool:
        """Send command to the device."""
        if self._api is None:
            # Local-only mode — UDP is the only transport.
            if not self.ip_address:
                _LOGGER.warning(
                    "No IP address known for %s yet; command dropped. "
                    "Waiting for the device to broadcast.",
                    self.name,
                )
                return False
        elif not self._options.get(CONF_USE_CLOUD_CONTROL, False) and self.ip_address:
            # Cloud mode with local preference: use UDP when IP is known.
            pass
        else:
            # Cloud mode (no local IP or cloud control forced).
            return await self._api.async_send_command(self.id, command)

        # UDP send path (local mode or cloud-with-local-preference).
        message = json.dumps(command).encode()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sent_bytes = sock.sendto(message, (self.ip_address, 5600))
            res = sent_bytes > 0
            if res:
                _LOGGER.debug(
                    "Command sent to %s (%s): %s",
                    self.name,
                    self.ip_address,
                    command,
                )
            else:
                _LOGGER.error(
                    "Failed to send command to %s (%s): %s",
                    self.name,
                    self.ip_address,
                    command,
                )
            return res

    async def async_request_state_refresh(self) -> bool:
        """Trigger a no-op command that makes the fan broadcast current state.

        Sending {"speedDelta": 0} prompts a fresh state broadcast from the device,
        but some fans treat it as a speed change and power on. It is therefore not
        called automatically; devices already broadcast their state periodically.
        """
        return await self._async_send_command({"speedDelta": 0})

    async def async_turn_on(self):
        """Turn on."""
        cmd = {ATTR_POWER: True}
        if await self._async_send_command(cmd):
            _LOGGER.debug("%s: turned on", self.name)
            self.update_state(cmd)

    async def async_turn_off(self):
        """Turn off."""
        cmd = {ATTR_POWER: False}
        if await self._async_send_command(cmd):
            _LOGGER.debug("%s: turned off", self.name)
            self.update_state(cmd)

    async def async_set_speed(self, value: int):
        """Set speed."""
        if value not in range(1, 7):
            raise ValueError("Value must in range of 1-6.")
        cmd = {ATTR_SPEED: value}
        if await self._async_send_command(cmd):
            _LOGGER.debug("%s: set speed %d", self.name, value)
            self.update_state(cmd)

    async def async_send_light_command(self, cmd: dict):
        """Send combined light command."""
        supported_cmds = {ATTR_LED, ATTR_LIGHT_MODE, ATTR_BRIGHTNESS}
        if not set(cmd.keys()).issubset(supported_cmds):
            raise ValueError(f"Supported commands are: {', '.join(supported_cmds)}")

        if len(cmd) > 1 and ATTR_LED in cmd:
            del cmd[ATTR_LED]

        if await self._async_send_command(cmd):
            _LOGGER.debug("%s: Light command executed successfully.", self.name)
            self.update_state(cmd)

    async def async_turn_on_sleep_mode(self):
        """Turn on sleep mode."""
        cmd = {ATTR_SLEEP: True}
        if await self._async_send_command(cmd):
            _LOGGER.debug("%s: turned on sleep mode", self.name)
            self.update_state(cmd)

    async def async_turn_off_sleep_mode(self):
        """Turn off sleep mode."""
        cmd = {ATTR_SLEEP: False}
        if await self._async_send_command(cmd):
            _LOGGER.debug("%s: turned off sleep mode", self.name)
            self.update_state(cmd)

    async def async_set_timer(self, value: int):
        """Set timer."""
        if value not in range(5):
            raise ValueError("Value must in range of 0-4.")
        if await self._async_send_command({"timer": value}):
            _LOGGER.debug("%s: set timer: %d", self.name, value)
            self.update_state({ATTR_TIMER_HOURS: TIMER_MAPPING[value][0]})

    def update_state(self, new_state: dict):
        """Update states."""
        if new_state.keys() - {ATTR_IS_ONLINE}:
            self._state_confirmed = True
        self._state.update(new_state)

    def restore_state(self, saved_state: dict) -> bool:
        """Restore a previously saved state unless a real one is already known."""
        if self._state_confirmed or not saved_state:
            return False
        self._state.update(saved_state)
        return True


def utc_seconds_to_local_time(value: int) -> time:
    """Convert a sleep window epoch value to local time of day."""
    # Only the UTC time of day (epoch modulo 86400) is used by the device
    utc_dt = datetime.combine(dt_util.utcnow().date(), time(), tzinfo=UTC)
    return dt_util.as_local(utc_dt + timedelta(seconds=value % 86400)).time()


def local_time_to_utc_seconds(value: time) -> int:
    """Convert a local time of day to sleep window epoch seconds."""
    local_dt = datetime.combine(
        dt_util.now().date(), value, tzinfo=dt_util.get_default_time_zone()
    )
    return int(dt_util.as_utc(local_dt).timestamp())


class AtombergPurifier:
    """Atomberg water purifier, controlled through cloud APIs only."""

    def __init__(self, data: dict[str, Any], api: AtombergCloudAPI) -> None:
        """Init Atomberg water purifier."""
        self._device_id = data["device_id"]
        self._series = data["series"]
        self._model = data.get("model")
        self._name = data.get("name") or self._device_id
        self._api = api
        self._state: dict = data["state"]
        self._supported_commands = {
            cmd["command"] for cmd in data.get("supported_commands") or []
        }
        # Sleep window times set while the window is off, sent when it's enabled
        self._pending_sleep_window: dict[str, int] = {}

    @property
    def state(self) -> dict[str, Any]:
        """Get state."""
        return deepcopy(self._state)

    @property
    def name(self) -> str:
        """Get name."""
        return self._name

    @property
    def id(self) -> str:
        """Get device_id."""
        return self._device_id

    @property
    def series(self) -> str:
        """Get series."""
        return self._series

    @property
    def model(self) -> str:
        """Get model."""
        return self._model

    @property
    def mac(self) -> str:
        """Get MAC address."""
        return format_mac(self.id)

    def update_state(self, new_state: dict):
        """Update states."""
        self._state.update(new_state)

    def supports(self, key: str) -> bool:
        """Check whether the device reports and accepts a setting."""
        if self._supported_commands and key not in self._supported_commands:
            return False
        return key in self._state

    def set_state(self, state: dict):
        """Replace state with the one reported by the cloud."""
        self._state = state

    def _sleep_window_values(self) -> tuple[int | None, int | None]:
        """Get sleep window start and stop epoch values, None when not set."""
        reported = (self._state.get(ATTR_START_UTC), self._state.get(ATTR_STOP_UTC))
        # A window that was never set is reported as start == stop (0, 0)
        if (
            reported[0] is None
            or reported[1] is None
            or (reported[0] % 86400 == reported[1] % 86400)
        ):
            reported = (None, None)
        return (
            self._pending_sleep_window.get(ATTR_START_UTC, reported[0]),
            self._pending_sleep_window.get(ATTR_STOP_UTC, reported[1]),
        )

    @property
    def sleep_window(self) -> tuple[time | None, time | None]:
        """Get the sleep window start and end as local times."""
        return tuple(
            utc_seconds_to_local_time(value) if value is not None else None
            for value in self._sleep_window_values()
        )

    async def _async_send_command(self, command: dict):
        """Send command to the device and update state optimistically."""
        await self._api.async_send_purifier_command(self.id, command)
        _LOGGER.debug("%s: command executed: %s", self.name, command)
        self.update_state(command)

    async def async_set_mode(self, value: int):
        """Set purification mode."""
        if value not in PURIFIER_MODES:
            raise ValueError(f"Mode must be one of {list(PURIFIER_MODES)}.")
        await self._async_send_command({ATTR_MODE: value})

    async def async_set_fallback_mode(self, value: int):
        """Set fallback mode."""
        if value not in PURIFIER_FALLBACK_MODES:
            raise ValueError(
                f"Fallback mode must be one of {list(PURIFIER_FALLBACK_MODES)}."
            )
        await self._async_send_command({ATTR_FALLBACK_MODE: value})

    async def async_set_tds_threshold(self, value: int):
        """Set input TDS threshold in ppm."""
        if not TDS_THRESHOLD_RANGE[0] <= value <= TDS_THRESHOLD_RANGE[1]:
            low, high = TDS_THRESHOLD_RANGE
            raise ValueError(f"TDS threshold must be in range of {low}-{high}.")
        await self._async_send_command({ATTR_TDS_THRESHOLD: value})

    async def async_set_idle_sleep(self, enabled: bool):
        """Enable or disable display sleep while idle."""
        await self._async_send_command({ATTR_IDLE_SLEEP: int(enabled)})

    async def async_set_sleep_window(self, enabled: bool):
        """Enable or disable the daily sleep window."""
        if not enabled:
            await self._async_send_command({ATTR_SLEEP_MODE: 0})
            return

        start, stop = self._sleep_window_values()
        if start is None or stop is None:
            raise HomeAssistantError("Set the sleep window start and end time first.")
        if start % 86400 == stop % 86400:
            raise HomeAssistantError("Sleep window start and end time must differ.")
        await self._async_send_command(
            {ATTR_SLEEP_MODE: 1, ATTR_START_UTC: start, ATTR_STOP_UTC: stop}
        )
        self._pending_sleep_window.clear()

    async def async_set_sleep_window_time(self, key: str, value: time):
        """Set sleep window start or end time."""
        if key not in (ATTR_START_UTC, ATTR_STOP_UTC):
            raise ValueError(f"Key must be {ATTR_START_UTC} or {ATTR_STOP_UTC}.")
        self._pending_sleep_window[key] = local_time_to_utc_seconds(value)

        # Apply right away only if the window is on, as sleep_mode=1 enables it
        if self._state.get(ATTR_SLEEP_MODE):
            await self.async_set_sleep_window(True)
