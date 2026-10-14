"""Support for number entities of Atomberg integration."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    EntityCategory,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device import ATTR_TDS_THRESHOLD, TDS_THRESHOLD_RANGE, AtombergPurifier
from .purifier_coordinator import AtombergPurifierCoordinator
from .purifier_entity import AtombergPurifierEntity, purifier_async_setup_entry


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Automatically setup the number entities from the devices list."""
    await purifier_async_setup_entry(
        hass,
        entry,
        async_add_entities,
        lambda coordinator, device: (
            [PurifierTdsThresholdNumber(coordinator, device)]
            if device.supports(ATTR_TDS_THRESHOLD)
            else []
        ),
    )


class PurifierTdsThresholdNumber(AtombergPurifierEntity, NumberEntity):
    """Water purifier input TDS threshold for RO vs UF treatment."""

    _attr_icon = "mdi:tune-vertical"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = TDS_THRESHOLD_RANGE[0]
    _attr_native_max_value = TDS_THRESHOLD_RANGE[1]
    _attr_native_step = 1
    _attr_native_unit_of_measurement = CONCENTRATION_PARTS_PER_MILLION

    def __init__(
        self, coordinator: AtombergPurifierCoordinator, device: AtombergPurifier
    ) -> None:
        """Initialize the entity."""
        super().__init__(
            coordinator, device, Platform.NUMBER, ATTR_TDS_THRESHOLD, "TDS threshold"
        )

    @property
    def native_value(self) -> int | None:
        """Get TDS threshold in ppm."""
        return self.device_state.get(ATTR_TDS_THRESHOLD)

    async def async_set_native_value(self, value: float) -> None:
        """Set TDS threshold."""
        await self._device.async_set_tds_threshold(int(value))
        self.async_write_ha_state()
