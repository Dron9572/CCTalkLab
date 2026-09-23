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

LOG_PATH = f"{os.path.abspath('')}/logs/emulHost_{datetime.now().strftime('%Y%m%d%H%M%S')}.log"

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
                write_log(f"RX actual: {response.hex(' ')}")
            else:
                write_log("RX actual: <none>")

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
    return host.command(0x01)

def enable_coins(host):

    # E7 FF 00
    #
    # FF = enable coins 1..8
    # 00 = disable coins 9..16
    #
    # This matches the configuration seen
    # in your SeciCCtalk log.

    return host.command(
        0xE7,
        bytes([0xFF, 0x00])
    )

def read_buffer(host):
    return host.command(0xE5)


# ============================================================
# Event parser
# ============================================================

class EventTracker:

    def __init__(self):

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
            write_log(f"E5 response is too short: {response.hex(" ")}")
            return

        # ----------------------------------------------------
        # Validate checksum
        # ----------------------------------------------------

        if sum(response) & 0xFF:
            write_log("WARNING: invalid checksum")

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        destination = response[0]
        length = response[1]
        source = response[2]
        reply_header = response[3]

        # ----------------------------------------------------
        # E5 data
        # ----------------------------------------------------

        event_counter = response[4]

        coin_number = response[5]
        sorter_path = response[6]

        # ----------------------------------------------------
        # First response
        # ----------------------------------------------------

        if self.last_event_counter is None:

            self.last_event_counter = event_counter

            if event_counter == 0:

                write_log("EVENT: POWER ON")

            else:
                write_log(f"Initial event counter: {event_counter}")

            return

        # ----------------------------------------------------
        # No new event
        # ----------------------------------------------------

        if event_counter == self.last_event_counter:
            return

        # ----------------------------------------------------
        # New event
        # ----------------------------------------------------

        self.last_event_counter = event_counter

        # ----------------------------------------------------
        # Event: credit / coin
        # ----------------------------------------------------

        if coin_number != 0:
            write_log("\n")
            write_log("=" * 40)
            write_log("COIN INSERTED")
            write_log(f"Event counter : {event_counter}")
            write_log(f"Coin number   : {coin_number}")
            write_log(f"Sorter path   : {sorter_path}")
            write_log("=" * 40)
            write_log("\n")

        # ----------------------------------------------------
        # Event: error
        # ----------------------------------------------------

        else:
            write_log("\n")
            write_log("=" * 40)
            write_log("COIN ACCEPTOR EVENT")
            write_log(f"Event counter : {event_counter}")
            write_log(f"Error code    : {sorter_path}")
            write_log("=" * 40)
            write_log("\n")

# ============================================================
# Main
# ============================================================

def main():
    write_log(f"CCtalk Host Emulator - version {APP_VERSION}")
    write_log("=" * 40)
    write_log(f"Port       : {PORT}")
    write_log(f"Baudrate   : {BAUDRATE}")
    write_log(f"Host       : {HOST_ADDRESS}")
    write_log(f"Device     : {COIN_ACCEPTOR_ADDRESS}")
    write_log("=" * 40)

    host = CCTalkHost(PORT)

    events = EventTracker()

    coin_status = 0

    try:

        write_log("\nInitializing coin acceptor...\n")

        # ----------------------------------------------------
        # Initialize
        # ----------------------------------------------------

        write_log("Checking coin acceptor...")

        response = simple_poll(host)

        if response:
            write_log("Coin acceptor is ONLINE\n")
            coin_status = 1

            response = request_serial_number(host)
            if response:
                write_log(f"\nCoin Serial Number {response}\n")
        else:
            write_log("WARNING: no response")
            coin_status = 0

        write_log("\n")

        # ----------------------------------------------------
        # Enable coins
        # ----------------------------------------------------

        write_log("Enabling coin channels...")

        response = enable_coins(host)

        if response:
            write_log("Coin channels enabled.")

        write_log("\n")

        # ----------------------------------------------------
        # Main loop
        # ----------------------------------------------------

        write_log("Host started.")
        write_log("Insert a coin.")
        write_log("Press Ctrl+C to exit.")
        write_log("\n")

        while True:

            # -----------------------------------------------
            # Read buffered events
            # -----------------------------------------------

            response = read_buffer(host)

            events.process(response)

            # -----------------------------------------------
            # Simple Poll
            # -----------------------------------------------

            simple_poll(host)
            # response = simple_poll(host)

            # if response:
            #     write_log("Coin acceptor is ONLINE\n")

            #     if response[3] == 0x00:
            #         write_log("From Slave: ACK")
                
            #     if coin_status == 0:
            #         write_log("FROM MASTER: Reset coin acceptor")
            #         response = reset_device(host)
            #         if response and response[3] == 0x00:
            #             coin_status = 1
                        
            #             response = request_serial_number(host)
            #             if response:
            #                 write_log(f"\nCoin Serial Number {response}\n")

            #     response = request_serial_number(host)
            #     if response:
            #         write_log(f"\nCoin Serial Number {response}\n")
            # else:
            #     write_log("WARNING: no response")
            #     coin_status = 0

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        write_log("Stopping...")

    finally:
        host.close()
        write_log("COM port closed.")


if __name__ == "__main__":
    main()