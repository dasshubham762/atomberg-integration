"""UDP Listener for Atomberg integration."""

import asyncio
import json
from logging import getLogger

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DISCOVERY_CALLBACK_KEY = "_discovery"

_LOGGER = getLogger(__name__)


class UDPListener(asyncio.DatagramProtocol):
    """UDP Listener."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Init UDP Listener."""
        self.hass = hass
        self.devices = {}
        self._listener = None
        self._callbacks = {}

    def parse_datagram(self, data, addr) -> tuple[str, str]:
        """Decode and parse the data."""
        message: str = data.decode(errors="ignore")

        if message.startswith("PROXY "):
            parts = message.split()
            if len(parts) >= 6 and parts[1] in ["TCP4"]:
                proxy_ip: str = parts[2]
                actual_message = " ".join(parts[6:])
                return actual_message, proxy_ip

        return message, addr[0]

    @staticmethod
    def _extract_device_details(device_id_field: str) -> dict[str, str]:
        """Extract device_id and optional series from raw device identifier.

        Some UDP payloads publish identifiers in the form `<device_id>_<series>`
        such as `<device_id>_R1`.
        """
        device_id_raw = device_id_field.strip()
        if not device_id_raw:
            return {}

        parts = device_id_raw.split("_", 1)
        details = {"device_id": parts[0]}
        if len(parts) > 1 and parts[1].strip():
            details["device_series"] = parts[1].strip().upper()
        return details

    def datagram_received(self, data, addr):
        """Decode data when broadcast received."""
        message, ip_addr = self.parse_datagram(data, addr)
        _LOGGER.debug("Message received %s from %s", message, ip_addr)

        # Try to hexdecode the message
        msg_data = {"ip_address": ip_addr}
        try:
            msg_data_bytes = bytes.fromhex(message)
            msg_data.update(json.loads(msg_data_bytes))
        except ValueError:
            msg_data.update(self._extract_device_details(message))

        # Normalize device metadata from any payload form.
        if device_id_field := msg_data.get("device_id"):
            msg_data.update(self._extract_device_details(device_id_field))

        for func in self._callbacks.values():
            func(msg_data)

    def add_callback(self, key: str | ConfigEntry, callback):
        """Add a callback keyed by entry_id or an arbitrary string."""
        key_str = key if isinstance(key, str) else key.entry_id
        self._callbacks[key_str] = callback

    def remove_callback(self, key: str | ConfigEntry):
        """Remove a callback keyed by entry_id or an arbitrary string."""
        key_str = key if isinstance(key, str) else key.entry_id
        self._callbacks.pop(key_str, None)

    async def start(self):
        """Start listening."""
        loop = asyncio.get_running_loop()
        self._listener = await loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 5625), reuse_port=True
        )
        _LOGGER.debug("Listening to broadcasts on UDP port 5625")

    def close(self):
        """Close listener."""
        if self._listener:
            self._callbacks.clear()
            self._listener[0].close()
            _LOGGER.debug("Closed UDP listener on port 5625")
