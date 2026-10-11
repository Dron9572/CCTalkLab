"""Serial transport used by CCTalkLab."""

import time

import serial


class SerialTransport:
    """Low-level serial transport.

    This class intentionally knows nothing about CCtalk devices or commands.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 0.05,
        echo_delay: float = 0.005,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.echo_delay = echo_delay

        self.serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )

        # Required by the current adapter/device setup.
        self.serial.dtr = True
        self.serial.rts = True

    def close(self) -> None:
        if self.serial.is_open:
            self.serial.close()

    def exchange(self, packet: bytes, read_size: int = 256) -> bytes:
        """Send bytes and return received bytes with adapter echo removed."""
        self.serial.reset_input_buffer()

        self.serial.write(packet)
        self.serial.flush()

        time.sleep(self.echo_delay)

        response = self.serial.read(read_size)

        if response.startswith(packet):
            response = response[len(packet):]

        return response

    def __enter__(self) -> "SerialTransport":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
