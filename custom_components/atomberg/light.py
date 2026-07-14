"""Support for Atomberg light entities."""

from logging import getLogger
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
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

# The fan LED supports 3 discrete color temperatures (warm, daylight and cool).
# Expose them on a full kelvin scale so that a color temperature selector shows
# up in the UI (and in HomeKit/Google Home via the respective bridges), and snap
# any requested value to the nearest mode supported by the device.
LIGHT_MODE_TO_KELVIN = {
    LIGHT_MODE_WARM: 2700,
    LIGHT_MODE_DAYLIGHT: 4000,
    LIGHT_MODE_COOL: 6500,
}
MIN_COLOR_TEMP_KELVIN = min(LIGHT_MODE_TO_KELVIN.values())
MAX_COLOR_TEMP_KELVIN = max(LIGHT_MODE_TO_KELVIN.values())


def kelvin_to_light_mode(kelvin: int) -> str:
    """Snap a kelvin value to the nearest light mode supported by the device."""
    return min(
        LIGHT_MODE_TO_KELVIN,
        key=lambda mode: abs(LIGHT_MODE_TO_KELVIN[mode] - kelvin),
    )


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
        if self._device.supports_color_effect:
            self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}
            self._attr_min_color_temp_kelvin = MIN_COLOR_TEMP_KELVIN
            self._attr_max_color_temp_kelvin = MAX_COLOR_TEMP_KELVIN
        elif self._device.supports_brightness_control:
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        else:
            self._attr_supported_color_modes = {ColorMode.ONOFF}

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
        if ColorMode.COLOR_TEMP in self.supported_color_modes:
            return ColorMode.COLOR_TEMP
        if ColorMode.BRIGHTNESS in self.supported_color_modes and self.brightness:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def color_temp_kelvin(self) -> int | None:
        """Get current color temperature in kelvin."""
        if light_mode := self.device_state.get(ATTR_LIGHT_MODE):
            return LIGHT_MODE_TO_KELVIN.get(light_mode)
        return None

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

        if color_temp := kwargs.get(ATTR_COLOR_TEMP_KELVIN):
            cmd[ATTR_LIGHT_MODE] = kelvin_to_light_mode(color_temp)

        await self._device.async_send_light_command(cmd)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off entity."""
        cmd = {ATTR_LED: False}
        await self._device.async_send_light_command(cmd)
