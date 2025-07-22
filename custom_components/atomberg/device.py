"""Device as wrapper for Atomberg Cloud APIs."""

import json
import socket
from copy import deepcopy
from logging import getLogger
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import AtombergCloudAPI
from .const import CONF_USE_CLOUD_CONTROL

_LOGGER = getLogger(__name__)

SUPPORTED_BRIGHTNESS_CONTROL_SERIES = ["I1"]
SUPPORTED_COLOR_EFFECT_SERIES = ["I1"]

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


class AtombergDevice:
    """Atomberg device."""

    def __init__(
        self,
        data: dict[str, Any],
        api: AtombergCloudAPI,
        config_entry: ConfigEntry = None,
    ) -> None:
        """Init Atomberg device."""
        self._device_id = data["device_id"]
        self._color = data["color"]
        self._series = data["series"]
        self._model = data["model"]
        self._name = data["name"]
        self._api = api
        self._state: dict = data["state"]
        self._last_seen: int = None
        self._ip_addr: str = None
        self._options = config_entry.options if config_entry else {}

        # Add options update listener
        if config_entry:
            config_entry.async_on_unload(
                config_entry.add_update_listener(self._update_options)
            )

    @property
    def supports_brightness_control(self):
        """Check whether device supports brightness control."""
        return self.series in SUPPORTED_BRIGHTNESS_CONTROL_SERIES

    @property
    def supports_color_effect(self):
        """Check whether device supports color modes."""
        return self.series in SUPPORTED_COLOR_EFFECT_SERIES

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
        if not self._options.get(CONF_USE_CLOUD_CONTROL, False) and self.ip_address:
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
        else:
            return await self._api.async_send_command(self.id, command)

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
        if await self._api.async_send_command(self.id, {"timer": value}):
            _LOGGER.debug("%s: set sleep mode: %d", self.name, value)
            self.update_state({ATTR_TIMER_HOURS: TIMER_MAPPING[value][0]})

    def update_state(self, new_state: dict):
        """Update states."""
        self._state.update(new_state)
