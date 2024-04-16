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

    def datagram_received(self, data, addr):
        """Decode data when broadcast received."""
        message = data.decode("utf-8")
        _LOGGER.debug("Message received: %s", message)

        # Try to hexdecode the message
        try:
            msg_data = bytes.fromhex(message)
            msg_data = json.loads(msg_data)
        except ValueError:
            msg_data = {"device_id": message.split("_")[0]}

        if self._callback:
            self._callback(msg_data)

    def set_callback(self, __func):
        """Get callback when a message is received."""
        self._callback = __func

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
