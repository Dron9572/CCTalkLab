"""CCtalk packet construction and validation."""

from dataclasses import dataclass


def checksum(data: bytes) -> int:
    """Return the CCtalk checksum byte for *data*."""
    return (-sum(data)) & 0xFF


def validate_checksum(packet: bytes) -> bool:
    """Return True when the complete packet has a valid CCtalk checksum."""
    return bool(packet) and (sum(packet) & 0xFF) == 0


def make_packet(destination: int, source: int, command: int, data: bytes = b"") -> bytes:
    """Build a CCtalk packet."""
    packet = bytearray()
    packet.append(destination)
    packet.append(len(data))
    packet.append(source)
    packet.append(command)
    packet.extend(data)
    packet.append(checksum(packet))
    return bytes(packet)


@dataclass(frozen=True)
class CCTalkPacket:
    """Decoded CCtalk packet."""

    destination: int
    length: int
    source: int
    command: int
    data: bytes
    checksum: int

    @classmethod
    def parse(cls, packet: bytes) -> "CCTalkPacket":
        if len(packet) < 5:
            raise ValueError("CCtalk packet is too short")

        length = packet[1]
        expected_length = length + 5

        if len(packet) != expected_length:
            raise ValueError(
                f"Invalid CCtalk packet length: expected {expected_length}, "
                f"got {len(packet)}"
            )

        if not validate_checksum(packet):
            raise ValueError("Invalid CCtalk checksum")

        return cls(
            destination=packet[0],
            length=length,
            source=packet[2],
            command=packet[3],
            data=packet[4:-1],
            checksum=packet[-1],
        )
