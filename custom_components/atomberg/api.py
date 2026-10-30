"""Cloud API for Atomberg."""

import datetime
import functools
from copy import deepcopy
from logging import getLogger
from typing import Literal

import jwt
import requests
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.dt import utcnow
from requests import Response

_LOGGER = getLogger(__name__)

API_VERSION = "v2"

DEVICE_TYPE_FAN = "fan"
DEVICE_TYPE_WATER_PURIFIER = "water_purifier"

SUPPORTED_SERIES = [
    "R1",
    "R2",
    "R3",
    "K1",
    "I1",
    "I2",
    "I3",
    "I4",
    "I5",
    "M1",
    "M2",
    "S1",
    "S2",
]


class AtombergCloudAPI:
    """Atomberg CloudAPI."""

    def __init__(self, hass: HomeAssistant, api_key: str, refresh_token: str) -> None:
        """Init Atomberg CloudAPI."""
        self._hass = hass
        self._base_url = "https://api.developer.atomberg-iot.com"
        self._api_key = api_key
        self._refresh_token = refresh_token
        self._access_token = None
        self.device_list: dict[str, dict] = {}
        self._device_types: dict[str, str] = {}

    async def test_connection(self):
        """Test API connection."""
        try:
            await self.async_sync_list_of_devices()
        except KeyError as e:
            _LOGGER.error("Atomberg Cloud authentication failed")
            raise InvalidAuth("Failed to authenticate") from e
        except Exception as e:
            _LOGGER.error("Atomberg Cloud connection test failed")
            raise CannotConnect("Failed to connect") from e

    async def async_get_access_token(self):
        """Get access token."""

        async def get_access_token():
            try:
                resp = await self.async_make_request(
                    f"/{API_VERSION}/get_access_token",
                    headers={"Authorization": f"Bearer {self._refresh_token}"},
                )
            except requests.exceptions.ConnectionError:
                return ConnectionError

            if not resp.ok:
                return

            data = resp.json()
            if data["status"] == "Success":
                self._access_token = resp.json()["message"]["access_token"]
                return self._access_token

        access_token_expired = False
        if self._access_token:
            try:
                access_token_data = jwt.decode(
                    self._access_token, options={"verify_signature": False}
                )
                exp_timestamp = access_token_data["exp"]
                exp_datetime = datetime.datetime.fromtimestamp(
                    exp_timestamp, datetime.UTC
                )
                access_token_expired = utcnow() > exp_datetime
            except jwt.ExpiredSignatureError:
                access_token_expired = True

            if not access_token_expired:
                return self._access_token

        return await get_access_token()

    async def async_make_request(
        self,
        url: str,
        method: Literal["GET", "POST"] = "GET",
        body: dict | None = None,
        headers: dict | None = None,
    ) -> Response:
        """Make a request."""
        headers_base = {
            "X-API-Key": self._api_key,
        }
        headers_extra = (
            headers
            if headers
            else {"Authorization": f"Bearer {await self.async_get_access_token()}"}
        )
        full_url = self._base_url + url

        match method:
            case "POST":
                func = functools.partial(
                    requests.post,
                    full_url,
                    headers=dict(headers_base, **headers_extra),
                    json=body,
                )
            case _:
                func = functools.partial(
                    requests.get, full_url, headers=dict(headers_base, **headers_extra)
                )

        resp = await self._hass.async_add_executor_job(func)
        if not resp.ok and resp.status_code < 500:
            try:
                error_msg = resp.json()["message"]
            except (ValueError, KeyError, TypeError):
                error_msg = resp.reason
            _LOGGER.error("Request failed due to %s", error_msg)
        return resp

    async def async_sync_list_of_devices(self) -> bool:
        """Get list of all devices connected to the account."""
        resp = await self.async_make_request(f"/{API_VERSION}/get_list_of_devices")

        data = resp.json()
        status = False
        if data.get("status") == "Success":
            supported_devices = []
            for dev in data["message"]["devices_list"]:
                if dev.get("device_type") == DEVICE_TYPE_WATER_PURIFIER:
                    supported_devices.append(dev)
                elif dev["series"] in SUPPORTED_SERIES:
                    supported_devices.append({**dev, "device_type": DEVICE_TYPE_FAN})
            self._device_types = {
                d["device_id"]: d["device_type"] for d in supported_devices
            }
            states = (
                await self.async_get_device_state(
                    [d["device_id"] for d in supported_devices]
                )
                or []
            )
            for dev in supported_devices:
                state = next(
                    filter(lambda x: x["device_id"] == dev["device_id"], states),
                    {"device_id": dev["device_id"]},
                )
                if state in states:
                    states.remove(state)
                self.device_list[state.pop("device_id")] = {**dev, "state": state}
            _LOGGER.info("Found %d atomberg devices", len(self.device_list))
            status = True
        else:  # noqa: RET505
            _LOGGER.error(
                "Atomberg devices sync failed due to '%s'. Please check API credentials",
                data["message"],
            )
        return status

    async def async_get_device_state(
        self, device_ids: list[str] | None = None
    ) -> list[dict] | None:
        """Get state of all/single device(s)."""
        resp = await self.async_make_request(
            f"/{API_VERSION}/get_device_state?device_id=all"
        )

        data = resp.json()
        if data["status"] == "Success":
            device_state = []
            for state in filter(
                lambda s: s["device_id"] in device_ids if device_ids else True,
                deepcopy(data["message"]["device_state"]),
            ):
                # Purifier states are cloud-only and are used as reported
                if self._device_types.get(state["device_id"]) == (
                    DEVICE_TYPE_WATER_PURIFIER
                ):
                    device_state.append(state)
                    continue

                # Keep is_online=False unless it's presense detected through udp broadcasts
                state["is_online"] = False
                # Rename some keys for ease of access
                state["speed"] = state.pop("last_recorded_speed")
                state["sleep"] = state.pop("sleep_mode")
                if state.get("last_recorded_brightness"):
                    state["brightness"] = state.pop("last_recorded_brightness")
                if state.get("last_recorded_color"):
                    state["light_mode"] = state.pop("last_recorded_color")
                device_state.append(state)

            return device_state

    async def async_send_command(self, device_id: str, command: dict) -> bool:
        """Send command to a device."""
        _LOGGER.debug("Sending command: '%s' to %s", command, device_id)
        payload = {"device_id": device_id, "command": command}
        resp = await self.async_make_request(
            f"/{API_VERSION}/send_command", "POST", body=payload
        )
        data = resp.json()
        return data["status"] == "Success"

    async def async_get_purifier_states(self) -> dict[str, dict]:
        """Get states of all water purifiers in a single API call."""
        resp = await self.async_make_request(
            f"/{API_VERSION}/get_device_state?device_id=all"
        )
        _raise_for_status(resp)

        return {
            state.pop("device_id"): state
            for state in resp.json()["message"]["device_state"]
            if self._device_types.get(state["device_id"]) == DEVICE_TYPE_WATER_PURIFIER
        }

    async def async_send_purifier_command(self, device_id: str, command: dict) -> None:
        """Send command to a water purifier, raising on failure."""
        _LOGGER.debug("Sending purifier command: '%s' to %s", command, device_id)
        payload = {"device_id": device_id, "command": command}
        resp = await self.async_make_request(
            f"/{API_VERSION}/send_command", "POST", body=payload
        )
        _raise_for_status(resp)

        try:
            data = resp.json()
        except ValueError as e:
            raise ApiError("Atomberg API returned an invalid response") from e
        if data.get("status") != "Success":
            raise ApiError(f"Atomberg API rejected the command: {data.get('message')}")


def _raise_for_status(resp: Response) -> None:
    """Raise an appropriate error for a failed API response."""
    if resp.ok:
        return

    try:
        message = resp.json()["message"]
    except (ValueError, KeyError, TypeError):
        message = resp.reason

    match resp.status_code:
        case 429:
            raise QuotaExceeded(f"Atomberg API quota exhausted: {message}")
        case 503:
            raise DeviceOffline(f"Device is offline: {message}")
        case _:
            raise ApiError(f"Atomberg API error {resp.status_code}: {message}")


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class ApiError(HomeAssistantError):
    """Error to indicate a failed API request."""


class QuotaExceeded(ApiError):
    """Error to indicate the daily API quota is exhausted."""


class DeviceOffline(ApiError):
    """Error to indicate the device is offline."""
