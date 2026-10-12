"""Coin acceptor implementation based on the working prototype."""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from ..host import CCTalkHost
from ..protocol import validate_checksum

@dataclass
class CoinChannelInfo:
    "Information read from one coin channel"

    channel: int
    coin_id: str | None = None
    enabled: bool | None = None
    response_hex: str | None = None
    error: str | None = None

@dataclass
class CoinAcceptorInfo:
    """Device identity and coin-channel information for UI/diagnostics"""

    manufacturer: str | None = None
    equipement: str | None = None
    product_code: str | None = None
    soft_version: str | None = None
    serial_number: int | None = None
    comms_revision: str | None = None
    coin_channels: list[CoinChannelInfo] = field(default_factory=list)
    creation_date: str | None = None
    build_code: str | None = None

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

    def request_manufacturer(self) -> bytes:
        return self.host.send_command(self.address, 0xF6)

    def request_equipement(self) -> bytes:
        return self.host.send_command(self.address, 0xF5)

    def request_product_code(self) -> bytes:
        return self.host.send_command(self.address, 0xF4)

    def request_soft_version(self) -> bytes:
        return self.host.send_command(self.address, 0xF1)

    def request_comms_revision(self) -> bytes:
        return self.host.send_command(self.address, 0x04)

    def request_base_year(self) -> bytes:
        return self.host.send_command(self.address, 0xAA)

    def request_creation_date(self) -> bytes:
        return self.host.send_command(self.address, 0xC4)
    
    def request_build_code(self) -> bytes:
        return self.host.send_command(self.address, 0xC0)

    def request_coin_id(self, channel: int) -> bytes:
        if not 1 <= channel <= 16:
            raise ValueError("Coin channel must be between 1 and 16")
        return self.host.send_command(self.address, 0xB8, bytes([channel]))

    def request_inhibit_status(self) -> bytes:
        return self.host.send_command(self.address, 0xE6)

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

    @staticmethod
    def _response_data(response: bytes) -> Optional[bytes]:
        """Return response payload after basic ccTalk frame validation."""
        if len(response) < 5 or not validate_checksum(response):
            return None
        expected_length = response[1] + 5
        if len(response) != expected_length:
            return None
        return response[4:-1]

    @classmethod
    def _response_text(cls, response: bytes) -> Optional[str]:
        data = cls._response_data(response)
        if data is None or not data:
            return None
        # Identity fields are specified as ASCII; replace non-ASCII bytes so
        # one unusual character does not prevent the rest of the info display.
        value = data.decode("ascii", errors="replace").strip("\x00 \t\r\n")
        return value or None

    def get_manufacturer(self) -> Optional[str]:
        return self._response_text(self.request_manufacturer())

    def get_equipement(self) -> Optional[str]:
        return self._response_text(self.request_equipement())

    def get_product_code(self) -> Optional[str]:
        return self._response_text(self.request_product_code())

    def get_soft_version(self) -> Optional[str]:
        return self._response_text(self.request_soft_version())

    def get_comms_revision(self) -> Optional[str]:
        """Decode header 4: [ccTalk level, major revision, minor revision]."""
        data = self._response_data(self.request_comms_revision())
        if data is None or len(data) != 3:
            return None
        return f"{data[0]}.{data[1]}.{data[2]}"

    def get_base_year(self) -> Optional[int]:
        value = self._response_text(self.request_base_year())

        if value is None:
            return None

        try:
            return int(value)
        except ValueError:
            return None

    def get_creation_date(self) -> Optional[str]:
        data = self._response_data(self.request_creation_date())

        if data is None or len(data) != 2:
            return None

        base_year = self.get_base_year()
        if base_year is None:
            return None

        date_code = int.from_bytes(data, byteorder="little")

        day = date_code & 0x1F
        month = (date_code >> 5) & 0x0F
        year = base_year + ((date_code >> 9) & 0x1F)

        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None
    
    def get_build_code(self) -> Optional[str]:
        return self._response_text(self.request_build_code())

    def get_inhibit_status(self) -> Optional[bytes]:
        """Return the two-byte channel mask, or None for an invalid response."""
        data = self._response_data(self.request_inhibit_status())
        if data is None or len(data) < 2:
            return None
        return data[:2]

    @staticmethod
    def _decode_coin_id(data: bytes) -> Optional[str]:
        """Decode the six-byte ASCII coin identifier returned by header 184."""
        if not data:
            return None
        try:
            value = data.decode("ascii").strip("\x00 \t\r\n")
        except UnicodeDecodeError:
            return data.hex(" ").upper()

        if not value or set(value) == {"."}:
            return None
        if not value.isprintable():
            return data.hex(" ").upper()
        return value

    def get_coin_channel_info(self, channel: int, inhibit_status: Optional[bytes] = None) -> CoinChannelInfo:
        response = self.request_coin_id(channel)
        data = self._response_data(response)
        if data is None:
            return CoinChannelInfo(channel=channel, error="No valid response")

        coin_id = self._decode_coin_id(data)
        enabled = None
        if inhibit_status is not None and len(inhibit_status) >= 2:
            mask_byte = inhibit_status[(channel - 1) // 8]
            enabled = bool(mask_byte & (1 << ((channel - 1) % 8)))


        return CoinChannelInfo(
            channel=channel,
            coin_id=coin_id,
            enabled=enabled,
            response_hex=data.hex(" ").upper(),
            error="No coin configured" if coin_id is None else None
        )

    def get_device_info(self, channel_count: int = 16) -> CoinAcceptorInfo:
        """Read supported identity fields and coin IDs without interrupting polling."""
        if not 1 <= channel_count <= 16:
            raise ValueError("channel_count must be between 1 and 16")

        info = CoinAcceptorInfo(
            serial_number=self.get_serial_number(),
            manufacturer=self.get_manufacturer(),
            equipement=self.get_equipement(),
            product_code=self.get_product_code(),
            comms_revision=self.get_comms_revision(),
            creation_date=self.get_creation_date(),
            build_code=self.get_build_code(),
            soft_version=self.get_soft_version()
        )

        inhibit_status = self.get_inhibit_status()
        for channel in range(1, channel_count + 1):
            info.coin_channels.append(self.get_coin_channel_info(channel, inhibit_status))

        return info
        
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
