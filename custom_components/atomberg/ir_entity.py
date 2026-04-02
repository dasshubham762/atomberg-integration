"""Base entity for Atomberg IR-controlled devices."""

from __future__ import annotations

import logging

from homeassistant.components.infrared import async_send_command
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change_event

from .atomberg_ir_codes import make_atomberg_command
from .const import (
    CONF_FAN_MODEL,
    CONF_IR_EMITTER_ENTITY,
    DOMAIN,
    FAN_MODEL_NAMES,
    MANUFACTURER,
)

_LOGGER = logging.getLogger(__name__)


class AtombergIrEntity(Entity):
    """Base entity for Atomberg IR-controlled devices."""

    _attr_has_entity_name = True
    _attr_assumed_state = True

    def __init__(self, entry: ConfigEntry, unique_id_suffix: str) -> None:
        """Initialize Atomberg IR entity."""
        self._infrared_entity_id = entry.data[CONF_IR_EMITTER_ENTITY]
        self._attr_unique_id = f"{entry.entry_id}_{unique_id_suffix}"

        fan_model = entry.data.get(CONF_FAN_MODEL, "generic")
        model_name = FAN_MODEL_NAMES.get(fan_model, "Atomberg Fan")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Atomberg {model_name}",
            manufacturer=MANUFACTURER,
            model=model_name,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to infrared entity state changes."""
        await super().async_added_to_hass()

        @callback
        def _async_ir_state_changed(event: Event[EventStateChangedData]) -> None:
            """Handle infrared entity state changes."""
            new_state = event.data["new_state"]
            ir_available = (
                new_state is not None and new_state.state != STATE_UNAVAILABLE
            )
            if ir_available != self.available:
                _LOGGER.debug(
                    "IR emitter %s used by %s is %s",
                    self._infrared_entity_id,
                    self.entity_id,
                    "available" if ir_available else "unavailable",
                )
                self._attr_available = ir_available
                self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._infrared_entity_id], _async_ir_state_changed
            )
        )

        ir_state = self.hass.states.get(self._infrared_entity_id)
        self._attr_available = (
            ir_state is not None and ir_state.state != STATE_UNAVAILABLE
        )

    async def _send_command(self, command_code: int) -> None:
        """Send an IR command to the Atomberg fan."""
        ir_command = make_atomberg_command(command_code)
        await async_send_command(
            self.hass,
            self._infrared_entity_id,
            ir_command,
            context=self._context,
        )
