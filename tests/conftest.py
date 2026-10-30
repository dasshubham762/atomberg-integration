"""Fixtures for Atomberg integration tests."""

import json
import time
from collections.abc import Generator
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.atomberg.const import (
    CONF_CONTROL_METHOD,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    ControlMethod,
)

FIXTURES = Path(__file__).parent / "fixtures"
PURIFIER_ID = "a0764ee4210c"
FAN_ID = "6867258b9d78"


def load_fixture(name: str) -> dict:
    """Load a JSON fixture."""
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""
    return


class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, status_code: int, body: Any) -> None:
        """Init fake response."""
        self.status_code = status_code
        self.ok = status_code < 400
        self.reason = "Fake"
        self._body = body

    def json(self) -> Any:
        """Get JSON body."""
        if self._body is None:
            raise ValueError("No JSON body")
        return self._body


class FakeCloud:
    """Fake Atomberg cloud API recording every call."""

    def __init__(self) -> None:
        """Init fake cloud."""
        self.devices = load_fixture("devices.json")
        self.states = load_fixture("states.json")
        self.calls: list[tuple[str, str, Any]] = []
        self.status_overrides: dict[str, int] = {}
        self.error_body_paths: set[str] = set()

    def _path(self, url: str) -> str:
        return url.split("/v2", 1)[1]

    def _respond(self, path: str, body: Any) -> FakeResponse:
        if path.split("?", 1)[0] in self.error_body_paths:
            return FakeResponse(200, {"status": "Error", "message": "Rejected"})
        if status := self.status_overrides.get(path.split("?", 1)[0]):
            return FakeResponse(status, {"status": "Error", "message": "Failed"})
        return FakeResponse(200, deepcopy(body))

    def get(self, url: str, headers: dict | None = None) -> FakeResponse:
        """Handle GET requests."""
        path = self._path(url)
        self.calls.append(("GET", path, None))
        if path == "/get_access_token":
            token = jwt.encode({"exp": int(time.time()) + 86400}, "x" * 32, "HS256")
            return self._respond(
                path, {"status": "Success", "message": {"access_token": token}}
            )
        if path == "/get_list_of_devices":
            return self._respond(path, self.devices)
        if path == "/get_device_state?device_id=all":
            return self._respond(path, self.states)
        return FakeResponse(404, {"status": "Error", "message": "Not found"})

    def post(
        self, url: str, headers: dict | None = None, json: Any = None
    ) -> FakeResponse:
        """Handle POST requests."""
        path = self._path(url)
        self.calls.append(("POST", path, json))
        return self._respond(
            path, {"status": "Success", "message": "Command sent successfully"}
        )

    @property
    def commands(self) -> list[dict]:
        """Get commands sent to the purifier."""
        return [
            body["command"]
            for method, _, body in self.calls
            if method == "POST" and body["device_id"] == PURIFIER_ID
        ]

    def count(self, path: str) -> int:
        """Count GET calls to a path."""
        return sum(1 for method, p, _ in self.calls if method == "GET" and p == path)

    def set_purifier_state(self, **values: Any) -> None:
        """Update the purifier state the cloud reports."""
        for state in self.states["message"]["device_state"]:
            if state["device_id"] == PURIFIER_ID:
                state.update(values)


@pytest.fixture
def cloud() -> Generator[FakeCloud]:
    """Patch HTTP calls with the fake cloud."""
    fake = FakeCloud()
    with (
        patch("custom_components.atomberg.api.requests.get", side_effect=fake.get),
        patch("custom_components.atomberg.api.requests.post", side_effect=fake.post),
    ):
        yield fake


@pytest.fixture
def mock_udp_listener() -> Generator[MagicMock]:
    """Avoid binding the UDP port in tests."""
    with patch("custom_components.atomberg.UDPListener") as listener_cls:
        listener_cls.return_value.start = AsyncMock()
        yield listener_cls.return_value


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Cloud config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_API_KEY: "api-key",
            CONF_REFRESH_TOKEN: "refresh-token",
            CONF_CONTROL_METHOD: ControlMethod.CLOUD,
        },
    )


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    cloud: FakeCloud,
    mock_udp_listener: MagicMock,
    config_entry: MockConfigEntry,
) -> MockConfigEntry:
    """Set up the integration with a fan and a purifier."""
    await hass.config.async_set_time_zone("Asia/Kolkata")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
