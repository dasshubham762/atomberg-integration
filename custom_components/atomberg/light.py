"""Support for Atomberg light entities."""

from logging import getLogger
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import scale_to_ranged_value, value_to_brightness

from .coordinator import AtombergDataUpdateCoordinator
from .device import (
    ATTR_LED,
    ATTR_LIGHT_MODE,
    LED_BRIGHTNESS_SCALE,
    LIGHT_MODE_COOL,
    LIGHT_MODE_DAYLIGHT,
    LIGHT_MODE_WARM,
    AtombergDevice,
)
from .entity import AtombergEntity, platform_async_setup_entry

_LOGGER = getLogger(__name__)

FAN_LED_EFFECTS = {
    LIGHT_MODE_DAYLIGHT.title(): LIGHT_MODE_DAYLIGHT,
    LIGHT_MODE_COOL.title(): LIGHT_MODE_COOL,
    LIGHT_MODE_WARM.title(): LIGHT_MODE_WARM,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Automatically setup the light entities from the devices list."""
    await platform_async_setup_entry(
        hass, entry, async_add_entities, AtombergFanLightEntity
    )


class AtombergFanLightEntity(AtombergEntity, LightEntity):
    """Light entity for Atomberg fans."""

    def __init__(
        self, coordinator: AtombergDataUpdateCoordinator, device: AtombergDevice
    ) -> None:
        """Init Light entity."""
        super().__init__(coordinator, device, _LOGGER)

        self._attr_name = self._device.name + " LED"
        self._attr_unique_id = self._get_unique_id(Platform.LIGHT, ATTR_LED)

        # Controls
        self._attr_supported_color_modes = {
            ColorMode.BRIGHTNESS
            if self._device.supports_brightness_control
            else ColorMode.ONOFF
        }

        # Light modes
        if self._device.supports_color_effect:
            self._attr_supported_features = LightEntityFeature.EFFECT
            self._attr_effect_list = list(FAN_LED_EFFECTS.keys())

    @property
    def is_on(self) -> bool:
        """Whether the fan LED is on."""
        return self.device_state[ATTR_LED]

    @property
    def brightness(self) -> int | None:
        """Get brightness in range 0..255."""
        if brightness := self.device_state.get(ATTR_BRIGHTNESS):
            return value_to_brightness(LED_BRIGHTNESS_SCALE, brightness)

    @property
    def color_mode(self) -> ColorMode:
        """Get current color mode."""
        if ColorMode.BRIGHTNESS in self.supported_color_modes and self.brightness:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def effect(self) -> str | None:
        """Get current effect."""
        if effect := self.device_state.get(ATTR_LIGHT_MODE):
            return list(FAN_LED_EFFECTS.keys())[
                list(FAN_LED_EFFECTS.values()).index(effect)
            ]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on entity."""
        cmd = {ATTR_LED: True}
        if brightness := kwargs.get(ATTR_BRIGHTNESS):
            cmd[ATTR_BRIGHTNESS] = round(
                scale_to_ranged_value((1, 255), LED_BRIGHTNESS_SCALE, brightness)
            )

        if effect := kwargs.get(ATTR_EFFECT):
            cmd[ATTR_LIGHT_MODE] = FAN_LED_EFFECTS[effect]

        await self._device.async_send_light_command(cmd)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off entity."""
        cmd = {ATTR_LED: False}
        await self._device.async_send_light_command(cmd)
