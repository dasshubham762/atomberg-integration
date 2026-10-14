"""Base Atomberg water purifier entity."""

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, PURIFIER_COORDINATORS
from .device import AtombergPurifier
from .purifier_coordinator import AtombergPurifierCoordinator

ATTR_IS_ONLINE = "is_online"


async def purifier_async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    entities_factory: Callable[
        [AtombergPurifierCoordinator, AtombergPurifier], Iterable[Entity]
    ],
) -> None:
    """Set up water purifier entities of a platform."""
    coordinator: AtombergPurifierCoordinator | None = (
        hass.data[DOMAIN].get(PURIFIER_COORDINATORS, {}).get(entry.entry_id)
    )
    if not coordinator:
        return

    async_add_entities(
        entity
        for device in coordinator.devices
        for entity in entities_factory(coordinator, device)
    )


class AtombergPurifierEntity(CoordinatorEntity[AtombergPurifierCoordinator]):
    """Atomberg water purifier base entity."""

    def __init__(
        self,
        coordinator: AtombergPurifierCoordinator,
        device: AtombergPurifier,
        platform: Platform,
        key: str,
        name: str,
    ) -> None:
        """Init Atomberg water purifier base entity."""
        super().__init__(coordinator)

        self._device = device
        device_unique_id = f"{MANUFACTURER}.{self._device.id}"
        self._attr_unique_id = f"{device_unique_id}_{key}_{platform}"
        self._attr_name = f"{self._device.name} {name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_unique_id)},
            connections={(dr.CONNECTION_NETWORK_MAC, self._device.mac)},
            name=self._device.name,
            manufacturer=MANUFACTURER,
            model=self._device.model,
        )

    @property
    def available(self) -> bool:
        """Whether the purifier is reachable."""
        return super().available and self.device_state.get(ATTR_IS_ONLINE) is not False

    @property
    def device_state(self) -> dict[str, Any]:
        """Get device state."""
        return self._device.state
