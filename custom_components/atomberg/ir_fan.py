"""Fan platform for Atomberg IR-controlled fans."""

from __future__ import annotations

import logging
import math

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .atomberg_ir_codes import SPEED_MAP, AtombergIRCommand
from .ir_entity import AtombergIrEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Atomberg IR fan from config entry."""
    async_add_entities([AtombergIrFanEntity(entry)])


class AtombergIrFanEntity(AtombergIrEntity, FanEntity):
    """Atomberg IR fan entity."""

    _attr_name = None
    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
    )
    _attr_speed_count = 6

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize Atomberg IR fan entity."""
        super().__init__(entry, unique_id_suffix="ir_fan")
        self._attr_is_on = False

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ) -> None:
        """Turn on the fan."""
        if not self._attr_is_on:
            await self._send_command(AtombergIRCommand.POWER)
            self._attr_is_on = True

        if percentage is not None:
            await self.async_set_percentage(percentage)
            return

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the fan."""
        if self._attr_is_on:
            await self._send_command(AtombergIRCommand.POWER)
            self._attr_is_on = False
            self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.async_turn_off()
            return

        if not self._attr_is_on:
            await self._send_command(AtombergIRCommand.POWER)
            self._attr_is_on = True

        speed = math.ceil(percentage / 100 * self._attr_speed_count)
        speed = max(1, min(speed, 6))

        await self._send_command(SPEED_MAP[speed])
        self.async_write_ha_state()
