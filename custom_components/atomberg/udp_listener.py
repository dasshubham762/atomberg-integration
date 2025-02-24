"""UDP Listener for Atomberg integration."""

import asyncio
import json
from logging import getLogger

from homeassistant.core import HomeAssistant

_LOGGER = getLogger(__name__)


class UDPListener(asyncio.DatagramProtocol):
    """UDP Listener."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Init UDP Listener."""
        self.hass = hass
        self.devices = {}
        self._listener = None
        self._callback = None

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
            msg_data.update({"device_id": message.split("_")[0]})

        if self._callback:
            self._callback(msg_data)

    def set_callback(self, callback):
        """Get callback when a message is received."""
        self._callback = callback

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
            self._callback = None
            self._listener[0].close()
            _LOGGER.debug("Closed UDP listener on port 5625")
