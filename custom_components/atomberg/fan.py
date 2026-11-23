"""Support for Atomberg Fans."""

from logging import getLogger
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import CONF_CONTROL_METHOD, ControlMethod
from .coordinator import AtombergDataUpdateCoordinator
from .device import ATTR_POWER, ATTR_SPEED, AtombergDevice
from .entity import AtombergEntity, platform_async_setup_entry
from .ir_fan import async_setup_entry as ir_fan_async_setup_entry

_LOGGER = getLogger(__name__)

# Atomberg fans support 6 distinct discrete speeds (1 to 6)
ORDERED_FAN_SPEEDS = list(range(1, 7))
PRESET_MODES = [str(s) for s in ORDERED_FAN_SPEEDS]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up fan entities — routes to IR or cloud/local implementation."""
    if entry.data.get(CONF_CONTROL_METHOD) == ControlMethod.IR:
        await ir_fan_async_setup_entry(hass, entry, async_add_entities)
        return

    await platform_async_setup_entry(hass, entry, async_add_entities, AtombergFanEntity)


class AtombergFanEntity(AtombergEntity, FanEntity):
    """Atomberg Fan Entity with percentage and preset speed control."""

    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
    )

    def __init__(
        self,
        coordinator: AtombergDataUpdateCoordinator,
        device: AtombergDevice,
    ) -> None:
        """Init Atomberg Fan."""
        super().__init__(coordinator, device, _LOGGER)

        self._attr_unique_id = self._get_unique_id(Platform.FAN)
        self._attr_name = self._device.name
        self._attr_speed_count = len(ORDERED_FAN_SPEEDS)
        self._attr_preset_modes = PRESET_MODES

    @property
    def is_on(self) -> bool:
        """Whether the fan is on."""
        return self.device_state.get(ATTR_POWER, False)

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return len(ORDERED_FAN_SPEEDS)

    @property
    def percentage(self) -> int | None:
        """Get fan speed in percentage (0 when fan is turned off)."""
        if not self.is_on:
            return 0
        speed = self.device_state.get(ATTR_SPEED, 1)
        if speed not in ORDERED_FAN_SPEEDS:
            speed = ORDERED_FAN_SPEEDS[0]
        return ordered_list_item_to_percentage(ORDERED_FAN_SPEEDS, speed)

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode corresponding to speed (1-6)."""
        if not self.is_on:
            return None
        speed = self.device_state.get(ATTR_SPEED)
        return str(speed) if speed in ORDERED_FAN_SPEEDS else str(ORDERED_FAN_SPEEDS[0])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device attributes."""
        return {
            "speed": self.device_state.get(ATTR_SPEED),
            "ip_address": self._device.ip_address,
        }

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self._device.async_turn_off()
        else:
            speed = percentage_to_ordered_list_item(
                ORDERED_FAN_SPEEDS, percentage=percentage
            )
            await self._device.async_set_speed(speed)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode (direct discrete speed 1-6)."""
        try:
            speed = int(preset_mode)
            if speed in ORDERED_FAN_SPEEDS:
                await self._device.async_set_speed(speed)
            else:
                _LOGGER.error("Invalid preset mode %s, expected 1-6", preset_mode)
        except (ValueError, TypeError):
            _LOGGER.error("Could not parse preset mode %s", preset_mode)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan, optionally setting speed via percentage or preset mode."""
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            await self._device.async_turn_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self._device.async_turn_off()

