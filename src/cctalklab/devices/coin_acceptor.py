"""Coin acceptor implementation based on the working prototype."""

from dataclasses import dataclass
from typing import Optional

from ..host import CCTalkHost
from ..protocol import validate_checksum

@dataclass(frozen=True)
class CoinEvent:
    event_counter: int
    coin_number: int
    sorter_path: int

    @property
    def is_coin_inserted(self) -> bool:
        return self.coin_number != 0

class CoinAcceptor:
    """CCtalk coin acceptor commands used by the current prototype."""

    def __init__(self, host: CCTalkHost, address: int = 2) -> None:
        self.host = host
        self.address = address

    def simple_poll(self) -> bytes:
        return self.host.poll(self.address)

    def request_serial_number(self) -> bytes:
        return self.host.send_command(self.address, 0xF2)

    def reset(self) -> bytes:
        return self.host.send_command(self.address, 0x01)

    def modify_sorter_path(self, coin_position: int, path: int = 1) -> bytes:
        return self.host.send_command(
            self.address,
            0xD2,
            bytes([coin_position, path]),
        )

    def modify_master_inhibit(self, status: int = 1) -> bytes:
        return self.host.send_command(
            self.address,
            0xE4,
            bytes([status]),
        )

    def enable_coins(self) -> bytes:
        return self.host.send_command(
            self.address,
            0xE7,
            bytes([0xFF, 0x00]),
        )

    def read_buffer(self) -> bytes:
        return self.host.send_command(self.address, 0xE5)

    def get_serial_number(self) -> Optional[int]:
        response = self.request_serial_number()

        if not response or len(response) < 8:
            return None

        if not validate_checksum(response):
            return None

        serial_bytes = response[4:-1]

        if len(serial_bytes) != 3:
            return None

        return int.from_bytes(serial_bytes, byteorder="little")

    def initialize(self) -> Optional[int]:
        """Initialize the device using the sequence from the prototype.

        Returns the serial number on success, otherwise None.
        """
        response = self.reset()

        if not response:
            return None

        # Preserve the timing used by the working prototype.
        import time
        time.sleep(0.2)

        serial_number = self.get_serial_number()

        if serial_number is None:
            return None

        response = self.modify_master_inhibit(status=1)

        if not response:
            return None

        time.sleep(0.125)

        response = self.enable_coins()

        if not response:
            return None

        return serial_number


class EventTracker:
    """Track E5 buffered events for a coin acceptor."""

    def __init__(self) -> None:
        self.last_event_counter: Optional[int] = None

    def reset(self) -> None:
        self.last_event_counter = None

    def process(self, response: bytes) -> Optional[CoinEvent]:
        if not response:
            return None

        if len(response) < 7:
            return None

        if not validate_checksum(response):
            return None

        event_counter = response[4]
        coin_number = response[5]
        sorter_path = response[6]

        if self.last_event_counter is None:
            self.last_event_counter = event_counter
            return None

        if event_counter == self.last_event_counter:
            return None

        self.last_event_counter = event_counter

        return CoinEvent(
            event_counter=event_counter,
            coin_number=coin_number,
            sorter_path=sorter_path,
        )
