"""Support for binary sensor entities of Atomberg integration."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device import ATTR_CHOKING_FAULTS, ATTR_SYSTEM_FAULTS, AtombergPurifier
from .purifier_coordinator import AtombergPurifierCoordinator
from .purifier_entity import AtombergPurifierEntity, purifier_async_setup_entry


@dataclass(frozen=True)
class PurifierFaultDescription:
    """Describes a binary sensor derived from a purifier fault object."""

    key: str
    name: str
    faults_key: str
    is_on: Callable[[dict[str, Any]], bool]
    device_class: BinarySensorDeviceClass | None = BinarySensorDeviceClass.PROBLEM
    icon: str | None = None
    show_codes: bool = False


PURIFIER_FAULTS = (
    PurifierFaultDescription(
        key="filter_choke",
        name="filter choked",
        faults_key=ATTR_CHOKING_FAULTS,
        is_on=lambda faults: bool(faults.get("filter_choke")),
        show_codes=True,
    ),
    PurifierFaultDescription(
        key="sv_fault",
        name="valve fault",
        faults_key=ATTR_CHOKING_FAULTS,
        is_on=lambda faults: bool(faults.get("sv_fault")),
        show_codes=True,
    ),
    PurifierFaultDescription(
        key="system_fault",
        name="system fault",
        faults_key=ATTR_SYSTEM_FAULTS,
        is_on=lambda faults: not faults.get("healthy", True),
        show_codes=True,
    ),
    PurifierFaultDescription(
        key="no_water",
        name="no water",
        faults_key=ATTR_SYSTEM_FAULTS,
        is_on=lambda faults: "NO_WATER" in faults.get("codes", []),
        icon="mdi:water-off",
    ),
    PurifierFaultDescription(
        key="tank_full",
        name="tank full",
        faults_key=ATTR_SYSTEM_FAULTS,
        is_on=lambda faults: "TANK_FULL" in faults.get("codes", []),
        device_class=None,
        icon="mdi:cup-water",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Automatically setup the binary sensor entities from the devices list."""
    await purifier_async_setup_entry(
        hass,
        entry,
        async_add_entities,
        lambda coordinator, device: [
            PurifierFaultBinarySensor(coordinator, device, description)
            for description in PURIFIER_FAULTS
        ],
    )


class PurifierFaultBinarySensor(AtombergPurifierEntity, BinarySensorEntity):
    """Water purifier fault binary sensor entity."""

    def __init__(
        self,
        coordinator: AtombergPurifierCoordinator,
        device: AtombergPurifier,
        description: PurifierFaultDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(
            coordinator,
            device,
            Platform.BINARY_SENSOR,
            description.key,
            description.name,
        )
        self._description = description
        self._attr_device_class = description.device_class
        self._attr_icon = description.icon

    @property
    def _faults(self) -> dict[str, Any] | None:
        """Get the decoded fault object, None if never reported."""
        return self.device_state.get(self._description.faults_key)

    @property
    def is_on(self) -> bool | None:
        """Whether the fault is present."""
        if (faults := self._faults) is None:
            return None
        return self._description.is_on(faults)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Get fault codes and descriptions."""
        if not self._description.show_codes or (faults := self._faults) is None:
            return None
        return {
            "codes": faults.get("codes", []),
            "descriptions": faults.get("descriptions", []),
            "raw": faults.get("raw"),
        }
