"""Device as wrapper for Atomberg Cloud APIs."""

from copy import deepcopy
from logging import getLogger
from typing import TYPE_CHECKING, Any

from homeassistant.core import callback

if TYPE_CHECKING:
    from .api import AtombergCloudAPI

_LOGGER = getLogger(__name__)


class AtombergDevice:
    """Atomberg device."""

    def __init__(self, data: dict[str, Any], **kwargs) -> None:
        """Init Atomberg device."""
        self._device_id = data["device_id"]
        self._color = data["color"]
        self._series = data["series"]
        self._model = data["model"]
        self._name = data["name"]
        self._api: "AtombergCloudAPI" = kwargs["api"]
        self._state: dict = data["state"]

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

    async def async_turn_on(self):
        """Turn on."""
        cmd = {"power": True}
        if await self._api.async_send_command(self.id, cmd):
            _LOGGER.debug("%s: turned on", self.name)
            self.async_update_state(cmd)

    async def async_turn_off(self):
        """Turn off."""
        cmd = {"power": False}
        if await self._api.async_send_command(self.id, cmd):
            _LOGGER.debug("%s: turned off", self.name)
            self.async_update_state(cmd)

    async def async_set_speed(self, value: int):
        """Set speed."""
        if value not in range(1, 7):
            raise ValueError("Value must in range of 1-6.")
        cmd = {"speed": value}
        if await self._api.async_send_command(self.id, cmd):
            _LOGGER.debug("%s: set speed %d", self.name, value)
            self.async_update_state(cmd)

    async def async_turn_on_light(self):
        """Turn on light."""
        cmd = {"led": True}
        if await self._api.async_send_command(self.id, cmd):
            _LOGGER.debug("%s: turned on LED", self.name)
            self.async_update_state(cmd)

    async def async_turn_off_light(self):
        """Turn off light."""
        cmd = {"led": False}
        if await self._api.async_send_command(self.id, cmd):
            _LOGGER.debug("%s: Turned off LED", self.name)
            self.async_update_state(cmd)

    async def async_turn_on_sleep_mode(self):
        """Turn on sleep mode."""
        cmd = {"sleep": True}
        if await self._api.async_send_command(self.id, cmd):
            _LOGGER.debug("%s: turned on sleep mode", self.name)
            self.async_update_state(cmd)

    async def async_turn_off_sleep_mode(self):
        """Turn off sleep mode."""
        cmd = {"sleep": False}
        if await self._api.async_send_command(self.id, cmd):
            _LOGGER.debug("%s: turned off sleep mode", self.name)
            self.async_update_state(cmd)

    async def async_set_timer(self, value: int):
        """Set timer."""
        if value not in range(5):
            raise ValueError("Value must in range of 0-4.")
        if await self._api.async_send_command(self.id, {"timer": value}):
            _LOGGER.debug("%s: set sleep mode: %d", self.name, value)
            self.async_update_state({"timer_hours": value})

    @callback
    def async_update_state(self, new_state: dict):
        """Update states."""
        self._state.update(new_state)
