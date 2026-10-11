"""Generic CCtalk host functionality."""

from .protocol import make_packet
from .serial import SerialTransport


class CCTalkHost:
    """CCtalk host/master independent of a specific device type."""

    def __init__(
        self,
        transport: SerialTransport,
        address: int = 1,
    ) -> None:
        self.transport = transport
        self.address = address

    def send_command(
        self,
        destination: int,
        command: int,
        data: bytes = b"",
    ) -> bytes:
        packet = make_packet(
            destination=destination,
            source=self.address,
            command=command,
            data=data,
        )
        return self.transport.exchange(packet)

    def poll(self, destination: int) -> bytes:
        return self.send_command(destination, 0xFE)
