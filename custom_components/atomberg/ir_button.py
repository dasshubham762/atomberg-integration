"""Button platform for Atomberg IR-controlled fans."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .atomberg_ir_codes import AtombergIRCommand
from .ir_entity import AtombergIrEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class AtombergIrButtonDescription(ButtonEntityDescription):
    """Describes an Atomberg IR button entity."""

    command_code: int


BUTTON_DESCRIPTIONS: tuple[AtombergIrButtonDescription, ...] = (
    AtombergIrButtonDescription(
        key="boost",
        translation_key="boost",
        command_code=AtombergIRCommand.BOOST,
    ),
    AtombergIrButtonDescription(
        key="led",
        translation_key="led",
        command_code=AtombergIRCommand.LED,
    ),
    AtombergIrButtonDescription(
        key="sleep",
        translation_key="sleep",
        command_code=AtombergIRCommand.SLEEP,
    ),
    AtombergIrButtonDescription(
        key="timer",
        translation_key="timer",
        command_code=AtombergIRCommand.TIMER,
    ),
    AtombergIrButtonDescription(
        key="timer_1h",
        translation_key="timer_1h",
        command_code=AtombergIRCommand.TIMER_1H,
    ),
    AtombergIrButtonDescription(
        key="timer_2h",
        translation_key="timer_2h",
        command_code=AtombergIRCommand.TIMER_2H,
    ),
    AtombergIrButtonDescription(
        key="timer_3h",
        translation_key="timer_3h",
        command_code=AtombergIRCommand.TIMER_3H,
    ),
    AtombergIrButtonDescription(
        key="timer_6h",
        translation_key="timer_6h",
        command_code=AtombergIRCommand.TIMER_6H,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Atomberg IR buttons from config entry."""
    async_add_entities(
        AtombergIrButton(entry, description) for description in BUTTON_DESCRIPTIONS
    )


class AtombergIrButton(AtombergIrEntity, ButtonEntity):
    """Atomberg IR button entity."""

    entity_description: AtombergIrButtonDescription

    def __init__(
        self,
        entry: ConfigEntry,
        description: AtombergIrButtonDescription,
    ) -> None:
        """Initialize Atomberg IR button."""
        super().__init__(entry, unique_id_suffix=f"ir_button_{description.key}")
        self.entity_description = description

    async def async_press(self) -> None:
        """Press the button."""
        await self._send_command(self.entity_description.command_code)
