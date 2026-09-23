import os
import serial
import time
from datetime import datetime

APP_VERSION = "0.1.2"

# ============================================================
# Configuration
# ============================================================

PORT = "COM3"

BAUDRATE = 9600

HOST_ADDRESS = 1
COIN_ACCEPTOR_ADDRESS = 2

POLL_INTERVAL = 0.1
SERIAL_TIMEOUT = 0.05

LOG_PATH = f"{os.path.abspath('')}/logs/emulHost_{APP_VERSION}_{datetime.now().strftime('%Y%m%d%H%M%S')}.log"

# ============================================================
# Utils
# ============================================================

def write_log(msg):
    print(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as file:
        file.write(f"{msg}\n")

# ============================================================
# CCtalk
# ============================================================

def checksum(data: bytes) -> int:
    return (-sum(data)) & 0xFF


def make_packet(destination, source, command, data=b""):
    packet = bytearray()

    packet.append(destination)
    packet.append(len(data))
    packet.append(source)
    packet.append(command)
    packet.extend(data)

    packet.append(checksum(packet))

    return bytes(packet)


# ============================================================
# Host
# ============================================================

class CCTalkHost:

    def __init__(self, port):

        self.serial = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.05,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )

        # Same as SeciCCtalk
        self.serial.dtr = True
        self.serial.rts = True

    def close(self):
        self.serial.close()

    def send(self, packet):

        write_log(f"TX: {packet.hex(' ')}")

        self.serial.reset_input_buffer()

        self.serial.write(packet)
        self.serial.flush()

        time.sleep(0.005)

        response = self.serial.read(256)

        if not response:
            write_log("RX: <timeout>")
            return b""

        write_log(f"RX: {response.hex(' ')}")

        # Remove adapter echo
        if response.startswith(packet):

            response = response[len(packet):]

            if response:
                write_log(f"RX actual: {response.hex(' ')}\n")
            else:
                write_log("RX actual: <none>\n")

        return response

    def command(self, command, data=b""):

        packet = make_packet(
            destination=COIN_ACCEPTOR_ADDRESS,
            source=HOST_ADDRESS,
            command=command,
            data=data,
        )

        return self.send(packet)


# ============================================================
# Commands
# ============================================================

def simple_poll(host):
    return host.command(0xFE)

def request_serial_number(host):
    return host.command(0xF2)

def reset_device(host):
    write_log("FROM MASTER: Reset device")
    return host.command(0x01)

def modify_sorter_path(host, coin_position, path=1):
    # Modify sorter paths coin position: 16  path1 to 1
    # Command D2: assign a coin position to a sorter path
    write_log(f"FROM MASTER: Modify sorter paths coin position: {coin_position}  path1 to {path}")
    return host.command(0xD2, bytes([coin_position, path]))

def modify_master_inhibit(host, status=1):
    # Modify master inhibit status '00000001'
    # Command E4: set master inhibit status.
    write_log(f"FROM MASTER: Modify master inhibit status '00000001'")
    return host.command(0xE4, bytes([status]))

def enable_coins(host):
    # Modify inhibit status '11111111' '00000000'
    # E7 FF 00
    #
    # FF = enable coins 1..8
    # 00 = disable coins 9..16
    #
    # This matches the configuration seen
    # in your SeciCCtalk log.
    write_log(f"FROM MASTER: Modify inhibit status '11111111' '00000000'")
    return host.command(0xE7, bytes([0xFF, 0x00]))

def read_buffer(host):
    write_log("FROM MASTER: Read buffered credit or error codes")
    return host.command(0xE5)


# ============================================================
# Event parser
# ============================================================

class EventTracker:

    def __init__(self):
        self.last_event_counter = None

    def reset(self):
        # After a device reset the event buffer/counter can start over.
        self.last_event_counter = None

    def process(self, response):

        if not response:
            return

        # Expected E5 response:
        #
        # 01 0B 02 00
        #    event counter
        #    result 1A
        #    result 1B
        #    ...
        #
        # Example:
        #
        # 01 0B 02 00 01 04 01 ...

        if len(response) < 7:
            write_log(f"E5 response is too short: {response.hex(' ')}")
            return

        if sum(response) & 0xFF:
            write_log("WARNING: invalid checksum")
            return

        event_counter = response[4]
        coin_number = response[5]
        sorter_path = response[6]

        # First E5 response after startup/recovery.
        if self.last_event_counter is None:
            self.last_event_counter = event_counter

            if event_counter == 0:
                write_log("EVENT: POWER ON")
            else:
                write_log(f"Initial event counter: {event_counter}")

            return

        # Same buffered event as last time.
        if event_counter == self.last_event_counter:
            return

        # New event.
        self.last_event_counter = event_counter

        if coin_number != 0:
            write_log("")
            write_log("=" * 40)
            write_log("COIN INSERTED")
            write_log(f"Event counter : {event_counter}")
            write_log(f"Coin number   : {coin_number}")
            write_log(f"Sorter path   : {sorter_path}")
            write_log("=" * 40)
            write_log("")
        else:
            write_log("")
            write_log("=" * 40)
            write_log("COIN ACCEPTOR EVENT")
            write_log(f"Event counter : {event_counter}")
            write_log(f"Error code    : {sorter_path}")
            write_log("=" * 40)
            write_log("")


# ============================================================
# Main
# ============================================================

def main():
    write_log(f"CCtalk Host Emulator - version {APP_VERSION}")
    write_log("=" * 40)
    write_log(f"Port       : {PORT}")
    write_log(f"Baudrate   : {BAUDRATE}")
    write_log(f"Host Addr  : {HOST_ADDRESS}")
    write_log(f"CA Addr    : {COIN_ACCEPTOR_ADDRESS}")
    write_log("=" * 40)
    write_log("")

    host = CCTalkHost(PORT)
    events = EventTracker()

    # Device state:
    # False = we currently consider the coin acceptor offline.
    # True  = the device has answered a poll and is initialized.
    coin_status = False
    serial_number = None

    def get_serial_number():
        # Request and decode the coin acceptor serial number.
        write_log("FROM MASTER: Request serial number")
        response = request_serial_number(host)

        if not response:
            write_log("WARNING: no response to serial number request")
            return None

        # Expected response for serial 5326681:
        # 01 03 02 00 59 47 51 09
        #
        # Payload is a 3-byte little-endian integer.
        if len(response) < 8:
            write_log(
                f"WARNING: invalid serial number response: "
                f"{response.hex(' ')}"
            )
            return None

        if sum(response) & 0xFF:
            write_log("WARNING: invalid serial number checksum")
            return None

        serial_bytes = response[4:-1]

        if len(serial_bytes) != 3:
            write_log(
                f"WARNING: unexpected serial number length: "
                f"{response.hex(' ')}"
            )
            return None

        serial = int.from_bytes(serial_bytes, byteorder="little")
        write_log("")
        write_log("=" * 40)
        write_log(f"Coin Serial Number: {serial}")
        write_log("=" * 40)
        write_log("")
        return serial

    def initialize_device():
        """
        Initialize a coin acceptor after it becomes available.

        Order:
            1. Reset device
            2. Wait briefly for reset
            3. Request serial number
            4. Enable coin channels

        The serial number is intentionally requested before enabling
        coin acceptance.
        """
        nonlocal serial_number
        write_log("")
        write_log("=" * 40)
        write_log("Initializing coin acceptor...")
        write_log("=" * 40)
        

        response = reset_device(host)

        if not response:
            write_log("WARNING: no response to reset")
            return False

        # Give the coin acceptor time to complete its reset.
        time.sleep(0.2)

        # The event buffer belongs to the old device state.
        events.reset()

        serial = get_serial_number()

        if serial is None:
            write_log("Initialization failed: serial number unavailable")
            return False

        serial_number = serial

        # SeciCCtalk configures every coin position from 16 down to 1
        # and assigns it to sorter path 1.
        # write_log("Configuring sorter paths...")

        # for coin_position in range(16, 0, -1):
        #     response = modify_sorter_path(host, coin_position, path=1)

        #     if not response:
        #         write_log(f"Initialization failed: sorter path position {coin_position} timeout")
        #         return False

        #     time.sleep(0.125)

        # SeciCCtalk then sets master inhibit status to 1.
        write_log("Setting master inhibit status...")

        response = modify_master_inhibit(host, status=1)

        if not response:
            write_log("Initialization failed: master inhibit timeout")
            return False

        time.sleep(0.125)

        write_log("Enabling coin channels...")

        response = enable_coins(host)

        if not response:
            write_log("Initialization failed: inhibit command timeout")
            return False

        write_log("Coin channels enabled.")
        write_log(f"Coin acceptor initialized successfully (serial: {serial_number})")
        write_log("=" * 40)
        write_log("")

        return True

    try:
        write_log("")
        write_log("=" * 40)
        write_log("Starting Host...")
        write_log("Waiting for coin acceptor...")
        write_log("=" * 40)
        write_log("")

        while True:

            # ------------------------------------------------
            # 1. Poll is the heartbeat.
            # ------------------------------------------------

            response = simple_poll(host)

            if not response:
                # If it was previously online, this is a transition
                # to OFFLINE. Do not repeatedly initialize here.
                if coin_status:
                    coin_status = False
                    serial_number = None

                    write_log("")
                    write_log("=" * 40)
                    write_log("WARNING: coin acceptor is OFFLINE")
                    write_log("Waiting for device to respond...")
                    write_log("=" * 40)
                    write_log("")

                time.sleep(POLL_INTERVAL)
                continue

            # ------------------------------------------------
            # 2. Device responded.
            #
            # If it was offline before, this is recovery.
            # A real host should reset and initialize it again.
            # ------------------------------------------------

            if not coin_status:
                write_log("")
                write_log("=" * 40)
                write_log("Coin acceptor is ONLINE")
                write_log("=" * 40)
                write_log("")

                if not initialize_device():
                    write_log(
                        "Initialization failed. "
                        "Device will be treated as OFFLINE."
                    )
                    coin_status = False

                    time.sleep(POLL_INTERVAL)
                    continue

                coin_status = True
                write_log("")
                write_log("=" * 40)
                write_log("Host started.")
                write_log("Insert a coin.")
                write_log("Press Ctrl+C to exit.")
                write_log("=" * 40)
                write_log("")

                # Do not immediately process E5 in the same iteration;
                # the reset has just happened and the device needs a
                # clean start of its event buffer.
                time.sleep(POLL_INTERVAL)
                continue

            # ------------------------------------------------
            # 3. Device is online and initialized.
            #    Read buffered credit/error events.
            # ------------------------------------------------

            response = read_buffer(host)

            events.process(response)

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        write_log("Stopping...")

    finally:
        host.close()
        write_log("COM port closed.")


if __name__ == "__main__":
    main()