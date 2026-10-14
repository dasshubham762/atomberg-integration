"""Support for sensor entities of Atomberg integration."""

from datetime import datetime
from logging import getLogger

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import UNIT_PPM
from .coordinator import AtombergDataUpdateCoordinator
from .device import (
    ATTR_INPUT_TDS,
    ATTR_TANK_TDS,
    ATTR_TIMER_HOURS,
    ATTR_TIMER_TIME_ELAPSED_MINS,
    ATTR_TS_EPOCH_SECONDS,
    AtombergDevice,
    AtombergPurifier,
)
from .entity import AtombergEntity, platform_async_setup_entry
from .purifier_coordinator import AtombergPurifierCoordinator
from .purifier_entity import AtombergPurifierEntity, purifier_async_setup_entry

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
    await purifier_async_setup_entry(
        hass,
        entry,
        async_add_entities,
        lambda coordinator, device: [
            PurifierTdsSensor(coordinator, device, ATTR_INPUT_TDS, "input TDS"),
            PurifierTdsSensor(coordinator, device, ATTR_TANK_TDS, "tank TDS"),
            *(
                [PurifierLastReportedSensor(coordinator, device)]
                if ATTR_TS_EPOCH_SECONDS in device.state
                else []
            ),
        ],
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


class PurifierTdsSensor(AtombergPurifierEntity, SensorEntity):
    """Water purifier TDS sensor entity."""

    _attr_icon = "mdi:water-opacity"
    _attr_native_unit_of_measurement = UNIT_PPM
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: AtombergPurifierCoordinator,
        device: AtombergPurifier,
        key: str,
        name: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, device, Platform.SENSOR, key, name)
        self._key = key

    @property
    def native_value(self) -> float | None:
        """Get TDS in ppm."""
        return self.device_state.get(self._key)


class PurifierLastReportedSensor(AtombergPurifierEntity, SensorEntity):
    """Water purifier last reported time sensor entity."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: AtombergPurifierCoordinator, device: AtombergPurifier
    ) -> None:
        """Initialize the entity."""
        super().__init__(
            coordinator, device, Platform.SENSOR, ATTR_TS_EPOCH_SECONDS, "last reported"
        )

    @property
    def native_value(self) -> datetime | None:
        """Get when the purifier last reported its state."""
        if (value := self.device_state.get(ATTR_TS_EPOCH_SECONDS)) is None:
            return None
        return dt_util.utc_from_timestamp(value)
