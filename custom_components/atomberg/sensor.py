"""Support for sensor entities of Atomberg integration."""

from logging import getLogger

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AtombergDataUpdateCoordinator
from .device import ATTR_TIMER_HOURS, ATTR_TIMER_TIME_ELAPSED_MINS, AtombergDevice
from .entity import AtombergEntity, platform_async_setup_entry

_LOGGER = getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Automatically setup the sensor entities from the devices list."""
    await platform_async_setup_entry(
        hass,
        entry,
        async_add_entities,
        TimerElapsedTimeSensor,
    )


class TimerElapsedTimeSensor(AtombergEntity, SensorEntity):
    """Timer elapsed time sensor entity."""

    def __init__(
        self, coordinator: AtombergDataUpdateCoordinator, device: AtombergDevice
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, device, _LOGGER)

        self._attr_unique_id = self._get_unique_id(
            Platform.SENSOR, suffix="timer_elapsed_time"
        )
        self._attr_name = self._device.name + " timer elapsed time"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_native_unit_of_measurement = "min"

    @property
    def icon(self) -> str:
        """Get icon dynamically."""
        icons = [
            "mdi:clock-time-twelve-outline",
            "mdi:clock-time-one-outline",
            "mdi:clock-time-two-outline",
            "mdi:clock-time-three-outline",
            "mdi:clock-time-four-outline",
            "mdi:clock-time-five-outline",
            "mdi:clock-time-six-outline",
            "mdi:clock-time-seven-outline",
            "mdi:clock-time-eight-outline",
            "mdi:clock-time-nine-outline",
            "mdi:clock-time-ten-outline",
            "mdi:clock-time-eleven-outline",
        ]
        timer_mins = self.device_state[ATTR_TIMER_HOURS] * 60
        if not timer_mins:
            return icons[0]

        return icons[round(self.native_value / timer_mins * (len(icons) - 1))]

    @property
    def native_value(self) -> int:
        """Get value in minutes."""
        return self.device_state[ATTR_TIMER_TIME_ELAPSED_MINS]
