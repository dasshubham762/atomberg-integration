"""Base Atomberg entity."""

import time

from homeassistant.const import Platform
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AtombergDataUpdateCoordinator
from .device import AtombergDevice

AVAILABILITY_TIMEOUT = 30


class AtombergEntity(CoordinatorEntity, Entity):
    """Atomberg base entity."""

    def __init__(
        self, coordinator: AtombergDataUpdateCoordinator, device: AtombergDevice
    ) -> None:
        """Init Atomberg base entity."""
        super().__init__(coordinator)

        self.hass = coordinator.hass
        self._device = device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._get_unique_id())},
            name=self._device.name,
            manufacturer=MANUFACTURER,
            model=self._device.model,
        )

    def _get_unique_id(
        self, platform: Platform | None = None, suffix: str | None = None
    ):
        unique_id = f"{MANUFACTURER}.{self._device.id}"
        if suffix:
            unique_id += f"_{suffix}"
        if platform:
            unique_id += f"_{platform}"
        return unique_id

    @property
    def available(self) -> bool:
        """Whether the entity is online."""
        return self._device.state["is_online"]

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data:
            if self.coordinator.data["device_id"] != self._device.id:
                return

            state = {}
            ha_state_update_required = False
            # Decode the state data
            if state_string := self.coordinator.data.get("state_string"):
                value = int(state_string.split(",")[0])

                state.update(
                    {
                        "power": (0x10) & value > 0,
                        "led": (0x20) & value > 0,
                        "sleep_mode": (0x80) & value > 0,
                        "speed": (0x07) & value,
                        "timer_hours": round((0x0F0000 & value) / 65536, 0),
                        "timer_time_elapsed_mins": round(
                            (0xFF000000 & value) * 4 / 16777216, 0
                        ),
                    }
                )

                ha_state_update_required = True

            # Update last seen time
            state.update({"is_online": True, "last_seen": int(time.time())})

            self._device.async_update_state(state)
            if ha_state_update_required or not self._device.state["is_online"]:
                self.async_schedule_update_ha_state()

        # In case of no data, update is_online state based on last_seen
        elif (
            last_seen := self._device.state.get("last_seen")
        ) and time.time() - last_seen > AVAILABILITY_TIMEOUT:
            self._device.async_update_state({"is_online": False})
            self.async_schedule_update_ha_state()
