"""Tests for Atomberg water purifier support."""

import importlib
from datetime import time, timedelta

import pytest
from homeassistant import const as ha_const
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.atomberg import const
from custom_components.atomberg.const import (
    CONF_CONTROL_METHOD,
    CONF_DEVICE_ID,
    CONF_DEVICE_SERIES,
    CONF_DISPLAY_NAME,
    CONF_PURIFIER_POLL_INTERVAL,
    DOMAIN,
    PURIFIER_COORDINATORS,
    ControlMethod,
)
from custom_components.atomberg.device import (
    local_time_to_utc_seconds,
    utc_seconds_to_local_time,
)

from .conftest import PURIFIER_ID, FakeCloud

PREFIX = "kitchen_purifier"
STATE_PATH = "/get_device_state?device_id=all"


async def test_setup_entities(
    hass: HomeAssistant, cloud: FakeCloud, setup_integration: MockConfigEntry
) -> None:
    """Purifier gets its own entities, fan entities stay on fans only."""
    entity_ids = {
        entry.entity_id
        for entry in er.async_entries_for_config_entry(
            er.async_get(hass), setup_integration.entry_id
        )
    }
    purifier_ids = {e for e in entity_ids if PREFIX in e}
    assert purifier_ids == {
        f"select.{PREFIX}_purification_mode",
        f"select.{PREFIX}_fallback_mode",
        f"number.{PREFIX}_tds_threshold",
        f"switch.{PREFIX}_idle_display_sleep",
        f"switch.{PREFIX}_sleep_window",
        f"time.{PREFIX}_sleep_window_start",
        f"time.{PREFIX}_sleep_window_end",
        f"sensor.{PREFIX}_input_tds",
        f"sensor.{PREFIX}_tank_tds",
        f"binary_sensor.{PREFIX}_filter_choked",
        f"binary_sensor.{PREFIX}_valve_fault",
        f"binary_sensor.{PREFIX}_system_fault",
        f"binary_sensor.{PREFIX}_no_water",
        f"binary_sensor.{PREFIX}_tank_full",
        f"button.{PREFIX}_refresh",
        f"sensor.{PREFIX}_last_reported",
    }
    # Fan entities are unchanged, lock is ignored
    assert "fan.bedroom_fan" in entity_ids
    assert "light.bedroom_fan_led" in entity_ids
    assert not any("front_door" in e for e in entity_ids)

    # Setup reuses the synced state instead of polling again
    assert cloud.count(STATE_PATH) == 1
    assert cloud.count("/get_access_token") == 1


async def test_states(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    """Purifier states are mapped from the cloud payload."""
    assert hass.states.get(f"select.{PREFIX}_purification_mode").state == (
        "TasteTune 100-150 ppm"
    )
    assert hass.states.get(f"select.{PREFIX}_fallback_mode").state == "RO only"
    assert hass.states.get(f"number.{PREFIX}_tds_threshold").state == "150"
    assert hass.states.get(f"switch.{PREFIX}_idle_display_sleep").state == STATE_ON
    assert hass.states.get(f"switch.{PREFIX}_sleep_window").state == STATE_OFF
    input_tds = hass.states.get(f"sensor.{PREFIX}_input_tds")
    assert input_tds.state == "412.0"
    assert input_tds.attributes["unit_of_measurement"] == "ppm"
    assert hass.states.get(f"sensor.{PREFIX}_tank_tds").state == "98.0"

    # 22:00 and 05:00 UTC in Asia/Kolkata
    assert hass.states.get(f"time.{PREFIX}_sleep_window_start").state == "03:30:00"
    assert hass.states.get(f"time.{PREFIX}_sleep_window_end").state == "10:30:00"


async def test_fault_sensors(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Fault objects are exposed as binary sensors."""
    filter_choked = hass.states.get(f"binary_sensor.{PREFIX}_filter_choked")
    assert filter_choked.state == STATE_ON
    assert filter_choked.attributes["codes"] == ["RO_CHOKE", "POST_RO_CHOKE"]
    assert filter_choked.attributes["device_class"] == "problem"
    assert hass.states.get(f"binary_sensor.{PREFIX}_valve_fault").state == STATE_OFF
    assert hass.states.get(f"binary_sensor.{PREFIX}_system_fault").state == STATE_OFF
    assert hass.states.get(f"binary_sensor.{PREFIX}_no_water").state == STATE_OFF
    assert hass.states.get(f"binary_sensor.{PREFIX}_tank_full").state == STATE_OFF


@pytest.mark.parametrize(
    ("domain", "service", "entity", "data", "command", "expected_state"),
    [
        (
            "select",
            "select_option",
            "select.kitchen_purifier_purification_mode",
            {"option": "RO only"},
            {"mode": 0},
            "RO only",
        ),
        (
            "select",
            "select_option",
            "select.kitchen_purifier_fallback_mode",
            {"option": "TasteTune 75-125 ppm"},
            {"fallback_mode": 3},
            "TasteTune 75-125 ppm",
        ),
        (
            "number",
            "set_value",
            "number.kitchen_purifier_tds_threshold",
            {"value": 200},
            {"tds_threshold": 200},
            "200",
        ),
        (
            "switch",
            "turn_off",
            "switch.kitchen_purifier_idle_display_sleep",
            {},
            {"idle_sleep": 0},
            STATE_OFF,
        ),
        (
            "switch",
            "turn_off",
            "switch.kitchen_purifier_sleep_window",
            {},
            {"sleep_mode": 0},
            STATE_OFF,
        ),
    ],
)
async def test_commands(  # noqa: PLR0917
    hass: HomeAssistant,
    cloud: FakeCloud,
    setup_integration: MockConfigEntry,
    domain: str,
    service: str,
    entity: str,
    data: dict,
    command: dict,
    expected_state: str,
) -> None:
    """Each control sends exactly one command key and updates state."""
    await hass.services.async_call(
        domain, service, {"entity_id": entity, **data}, blocking=True
    )
    assert cloud.commands == [command]
    assert hass.states.get(entity).state == expected_state


async def test_sleep_window(
    hass: HomeAssistant, cloud: FakeCloud, setup_integration: MockConfigEntry
) -> None:
    """Times are held while the window is off and sent with sleep_mode=1."""
    start_entity = f"time.{PREFIX}_sleep_window_start"
    await hass.services.async_call(
        "time", "set_value", {"entity_id": start_entity, "time": "22:30:00"}, True
    )
    # Window is off, so nothing is sent yet
    assert cloud.commands == []
    assert hass.states.get(start_entity).state == "22:30:00"

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": f"switch.{PREFIX}_sleep_window"}, True
    )
    [command] = cloud.commands
    assert command["sleep_mode"] == 1
    assert utc_seconds_to_local_time(command["start_utc"]) == time(22, 30)
    assert command["stop_utc"] == 1767330000

    # With the window on, a time change is sent right away
    await hass.services.async_call(
        "time",
        "set_value",
        {"entity_id": f"time.{PREFIX}_sleep_window_end", "time": "06:00:00"},
        True,
    )
    command = cloud.commands[-1]
    assert set(command) == {"sleep_mode", "start_utc", "stop_utc"}
    assert utc_seconds_to_local_time(command["stop_utc"]) == time(6, 0)


async def test_sleep_window_never_set(
    hass: HomeAssistant, cloud: FakeCloud, mock_udp_listener, config_entry
) -> None:
    """A window reported as start == stop is treated as not set."""
    cloud.set_purifier_state(start_utc=0, stop_utc=0)
    config_entry.add_to_hass(hass)
    await hass.config.async_set_time_zone("Asia/Kolkata")
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    start_entity = f"time.{PREFIX}_sleep_window_start"
    end_entity = f"time.{PREFIX}_sleep_window_end"
    assert hass.states.get(start_entity).state == "unknown"
    assert hass.states.get(end_entity).state == "unknown"

    switch = {"entity_id": f"switch.{PREFIX}_sleep_window"}
    with pytest.raises(HomeAssistantError, match="first"):
        await hass.services.async_call("switch", "turn_on", switch, blocking=True)

    await hass.services.async_call(
        "time", "set_value", {"entity_id": start_entity, "time": "23:00:00"}, True
    )
    with pytest.raises(HomeAssistantError, match="first"):
        await hass.services.async_call("switch", "turn_on", switch, blocking=True)

    await hass.services.async_call(
        "time", "set_value", {"entity_id": end_entity, "time": "06:00:00"}, True
    )
    await hass.services.async_call("switch", "turn_on", switch, blocking=True)
    [command] = cloud.commands
    assert utc_seconds_to_local_time(command["start_utc"]) == time(23, 0)
    assert utc_seconds_to_local_time(command["stop_utc"]) == time(6, 0)
    assert hass.states.get("switch.kitchen_purifier_sleep_window").state == STATE_ON


async def test_offline_purifier_unavailable(
    hass: HomeAssistant, cloud: FakeCloud, setup_integration: MockConfigEntry
) -> None:
    """Entities go unavailable when the cloud reports the purifier offline."""
    cloud.set_purifier_state(is_online=False)
    await hass.services.async_call(
        "button", "press", {"entity_id": f"button.{PREFIX}_refresh"}, True
    )
    await hass.async_block_till_done()
    assert hass.states.get(f"sensor.{PREFIX}_tank_tds").state == STATE_UNAVAILABLE


async def test_refresh_and_quota_exhausted(
    hass: HomeAssistant, cloud: FakeCloud, setup_integration: MockConfigEntry
) -> None:
    """Refresh polls the cloud; a 429 marks entities unavailable."""
    cloud.set_purifier_state(tank_tds=120.0)
    await hass.services.async_call(
        "button", "press", {"entity_id": f"button.{PREFIX}_refresh"}, True
    )
    await hass.async_block_till_done()
    assert cloud.count(STATE_PATH) == 2
    assert hass.states.get(f"sensor.{PREFIX}_tank_tds").state == "120.0"

    cloud.status_overrides["/get_device_state"] = 429
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()
    assert cloud.count(STATE_PATH) == 3
    assert hass.states.get(f"sensor.{PREFIX}_tank_tds").state == STATE_UNAVAILABLE
    # Refresh stays usable to recover
    assert hass.states.get(f"button.{PREFIX}_refresh").state != STATE_UNAVAILABLE


async def test_polling_interval(
    hass: HomeAssistant, cloud: FakeCloud, setup_integration: MockConfigEntry
) -> None:
    """Purifier is polled on the configured interval."""
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=29))
    await hass.async_block_till_done()
    assert cloud.count(STATE_PATH) == 1

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=31))
    await hass.async_block_till_done()
    assert cloud.count(STATE_PATH) == 2

    hass.config_entries.async_update_entry(
        setup_integration, options={CONF_PURIFIER_POLL_INTERVAL: 60}
    )
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][PURIFIER_COORDINATORS][setup_integration.entry_id]
    assert coordinator.update_interval == timedelta(minutes=60)


async def test_offline_command_raises(
    hass: HomeAssistant, cloud: FakeCloud, setup_integration: MockConfigEntry
) -> None:
    """A command to an offline purifier surfaces an error."""
    cloud.status_overrides["/send_command"] = 503
    with pytest.raises(HomeAssistantError, match="offline"):
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": f"select.{PREFIX}_purification_mode", "option": "Vacation"},
            blocking=True,
        )
    assert hass.states.get(f"select.{PREFIX}_purification_mode").state == (
        "TasteTune 100-150 ppm"
    )


async def test_older_firmware_without_optional_fields(
    hass: HomeAssistant, cloud: FakeCloud, mock_udp_listener, config_entry
) -> None:
    """Firmware-dependent settings are skipped when not reported."""
    for state in cloud.states["message"]["device_state"]:
        if state["device_id"] == PURIFIER_ID:
            for key in ("tds_threshold", "sleep_mode", "start_utc", "stop_utc"):
                del state[key]
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(f"select.{PREFIX}_purification_mode") is not None
    assert hass.states.get(f"number.{PREFIX}_tds_threshold") is None
    assert hass.states.get(f"switch.{PREFIX}_sleep_window") is None
    assert hass.states.get(f"time.{PREFIX}_sleep_window_start") is None


async def test_unload(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    """Unloading removes the purifier coordinator."""
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert setup_integration.entry_id not in hass.data[DOMAIN][PURIFIER_COORDINATORS]


async def test_time_conversion_roundtrip(hass: HomeAssistant) -> None:
    """Local time of day survives conversion to epoch seconds and back."""
    await hass.config.async_set_time_zone("Asia/Kolkata")
    for value in (time(0, 0), time(3, 30), time(22, 15), time(23, 59)):
        assert utc_seconds_to_local_time(local_time_to_utc_seconds(value)) == value


def test_ppm_unit_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ppm unit is defined on Home Assistant versions without UnitOfRatio."""
    monkeypatch.delattr(ha_const, "UnitOfRatio")
    try:
        assert importlib.reload(const).UNIT_PPM == "ppm"
    finally:
        monkeypatch.undo()
        importlib.reload(const)
    assert const.UNIT_PPM == "ppm"


async def test_local_udp_entry_unaffected(
    hass: HomeAssistant, cloud: FakeCloud, mock_udp_listener
) -> None:
    """Local UDP entries set up without purifier entities or cloud calls."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_CONTROL_METHOD: ControlMethod.LOCAL_UDP,
            CONF_DEVICE_ID: "3844be556628",
            CONF_DEVICE_SERIES: "R3",
            CONF_DISPLAY_NAME: "Work room fan",
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("fan.work_room_fan") is not None
    assert not [s for s in hass.states.async_all() if "purifier" in s.entity_id]
    assert cloud.calls == []
    assert PURIFIER_COORDINATORS not in hass.data[DOMAIN]
