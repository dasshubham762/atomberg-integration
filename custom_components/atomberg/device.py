"""Device as wrapper for Atomberg Cloud APIs."""

from copy import deepcopy
from logging import getLogger
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS

from .api import AtombergCloudAPI

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
LED_BRIGHTNESS_SCALE = (10, 100)
TIMER_MAPPING = [
    (0, "Off"),
    (1, "1 hour"),
    (2, "2 hours"),
    (3, "3 hours"),
    (6, "6 hours"),
]


class AtombergDevice:
    """Atomberg device."""

    def __init__(self, data: dict[str, Any], api: AtombergCloudAPI) -> None:
        """Init Atomberg device."""
        self._device_id = data["device_id"]
        self._color = data["color"]
        self._series = data["series"]
        self._model = data["model"]
        self._name = data["name"]
        self._api = api
        self._state: dict = data["state"]
        self._last_seen: int = None

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

    def update_last_seen(self, __value: float):
        """Update last seen timestamp."""
        self._last_seen = __value

    async def async_turn_on(self):
        """Turn on."""
        cmd = {ATTR_POWER: True}
        if await self._api.async_send_command(self.id, cmd):
            _LOGGER.debug("%s: turned on", self.name)
            self.update_state(cmd)

    async def async_turn_off(self):
        """Turn off."""
        cmd = {ATTR_POWER: False}
        if await self._api.async_send_command(self.id, cmd):
            _LOGGER.debug("%s: turned off", self.name)
            self.update_state(cmd)

    async def async_set_speed(self, value: int):
        """Set speed."""
        if value not in range(1, 7):
            raise ValueError("Value must in range of 1-6.")
        cmd = {ATTR_SPEED: value}
        if await self._api.async_send_command(self.id, cmd):
            _LOGGER.debug("%s: set speed %d", self.name, value)
            self.update_state(cmd)

    async def async_send_light_command(self, cmd: dict):
        """Send combined light command."""
        supported_cmds = {ATTR_LED, ATTR_LIGHT_MODE, ATTR_BRIGHTNESS}
        if not set(cmd.keys()).issubset(supported_cmds):
            raise ValueError(f"Supported commands are: {', '.join(supported_cmds)}")

        if await self._api.async_send_command(self.id, cmd):
            _LOGGER.debug("%s: Light command executed successfully.", self.name)
            self.update_state(cmd)

    async def async_turn_on_sleep_mode(self):
        """Turn on sleep mode."""
        cmd = {ATTR_SLEEP: True}
        if await self._api.async_send_command(self.id, cmd):
            _LOGGER.debug("%s: turned on sleep mode", self.name)
            self.update_state(cmd)

    async def async_turn_off_sleep_mode(self):
        """Turn off sleep mode."""
        cmd = {ATTR_SLEEP: False}
        if await self._api.async_send_command(self.id, cmd):
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
