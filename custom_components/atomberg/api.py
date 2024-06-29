"""Cloud API for Atomberg."""

import datetime
import functools
from copy import deepcopy
from logging import getLogger
from typing import Literal

import jwt
import requests
from homeassistant.core import HomeAssistant
from homeassistant.util.dt import utcnow
from requests import Response

_LOGGER = getLogger(__name__)


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

    async def test_connection(self):
        """Test API connection."""
        if not await self.async_sync_list_of_devices():
            _LOGGER.error("Atomberg Cloud connection test failed")
            return False
        return True

    async def async_get_access_token(self):
        """Get access token."""

        async def get_access_token():
            try:
                resp = await self.async_make_request(
                    "/v1/get_access_token",
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
            error_msg = resp.json()["message"]
            _LOGGER.error("Request failed due to %s", error_msg)
        return resp

    async def async_sync_list_of_devices(self) -> bool:
        """Get list of all devices connected to the account."""
        resp = await self.async_make_request("/v1/get_list_of_devices")

        data = resp.json()
        status = False
        if data.get("status") == "Success":
            states = await self.async_get_device_state()
            for dev in data["message"]["devices_list"]:
                state = next(
                    filter(lambda x: x["device_id"] == dev["device_id"], states)
                )
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

    async def async_get_device_state(self, device_id: str = "all") -> list[dict] | None:
        """Get state of all/single device(s)."""
        resp = await self.async_make_request(
            f"/v1/get_device_state?device_id={device_id}"
        )

        data = resp.json()
        if data["status"] == "Success":
            device_state = []
            for state in deepcopy(data["message"]["device_state"]):
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
        resp = await self.async_make_request("/v1/send_command", "POST", body=payload)
        data = resp.json()
        return data["status"] == "Success"
