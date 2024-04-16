"""UDP Listener for Atomberg integration."""

import asyncio
import json
from logging import getLogger

from homeassistant.core import HomeAssistant

_LOGGER = getLogger(__name__)


class UDPListener(asyncio.DatagramProtocol):
    """UDP Listener."""

    def __init__(self, hass: HomeAssistant, __callback) -> None:
        """Init UDP Listener."""
        self.hass = hass
        self.devices = {}
        self._listener = []
        self._callback = __callback

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

        self._callback(msg_data)

    async def start(self):
        """Start listening."""
        loop = asyncio.get_running_loop()
        self._listener = await loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 5625), reuse_port=True
        )
        _LOGGER.debug("Listening to broadcasts on UDP port 5625")
