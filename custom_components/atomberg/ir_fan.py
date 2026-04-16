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
    """Atomberg IR fan entity with optimistic/assumed state management."""

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
        # percentage=0 means off; FanEntity.is_on is derived from percentage > 0
        self._attr_percentage = 0
        # Tracks the last non-zero speed so Turn On can resume at it
        self._last_on_percentage: int = round(100 / self._attr_speed_count)  # speed 1

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ) -> None:
        """Turn on the fan."""
        await self._send_command(AtombergIRCommand.POWER)
        if percentage is not None:
            await self.async_set_percentage(percentage)
            return
        # Resume at last known speed (defaults to speed 1 on first use)
        self._attr_percentage = self._last_on_percentage
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the fan."""
        await self._send_command(AtombergIRCommand.POWER)
        self._attr_percentage = 0
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.async_turn_off()
            return

        # If currently off, send power-on first
        if self._attr_percentage == 0:
            await self._send_command(AtombergIRCommand.POWER)

        speed = max(1, min(6, math.ceil(percentage / 100 * self._attr_speed_count)))
        await self._send_command(SPEED_MAP[speed])

        self._attr_percentage = percentage
        self._last_on_percentage = percentage
        self.async_write_ha_state()
