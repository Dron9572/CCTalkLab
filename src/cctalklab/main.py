"""CCTalkLab command-line entry point for the current core prototype."""

import logging
import time

from .devices.coin_acceptor import CoinAcceptor, EventTracker
from .host import CCTalkHost
from .serial import SerialTransport

APP_VERSION = "0.1.0"

PORT = "COM11"
BAUDRATE = 9600

HOST_ADDRESS = 1
COIN_ACCEPTOR_ADDRESS = 2

POLL_INTERVAL = 0.1
SERIAL_TIMEOUT = 0.05

def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

def main() -> None:
    configure_logging()
    log = logging.getLogger("cctalklab")

    log.info("CCTalkLab - version %s", APP_VERSION)
    log.info("=" * 40)
    log.info("Port       : %s", PORT)
    log.info("Baudrate   : %s", BAUDRATE)
    log.info("Host Addr  : %s", HOST_ADDRESS)
    log.info("CA Addr    : %s", COIN_ACCEPTOR_ADDRESS)
    log.info("=" * 40)

    transport = SerialTransport(
        port=PORT,
        baudrate=BAUDRATE,
        timeout=SERIAL_TIMEOUT,
    )
    host = CCTalkHost(
        transport=transport,
        address=HOST_ADDRESS,
    )
    coin_acceptor = CoinAcceptor(
        host=host,
        address=COIN_ACCEPTOR_ADDRESS,
    )
    events = EventTracker()

    coin_status = False
    serial_number = None

    try:
        log.info("Starting Host...")
        log.info("Waiting for coin acceptor...")

        while True:
            response = coin_acceptor.simple_poll()

            if not response:
                if coin_status:
                    coin_status = False
                    serial_number = None
                    log.warning("Coin acceptor is OFFLINE")
                    log.info("Waiting for device to respond...")

                time.sleep(POLL_INTERVAL)
                continue

            if not coin_status:
                log.info("Coin acceptor is ONLINE")
                log.info("Initializing coin acceptor...")

                events.reset()
                serial_number = coin_acceptor.initialize()

                if serial_number is None:
                    log.warning(
                        "Initialization failed. "
                        "Device will be treated as OFFLINE."
                    )
                    coin_status = False
                    time.sleep(POLL_INTERVAL)
                    continue

                coin_status = True

                log.info(
                    "Coin acceptor initialized successfully "
                    "(serial: %s)",
                    serial_number,
                )
                log.info("Host started.")
                log.info("Insert a coin.")
                log.info("Press Ctrl+C to exit.")

                time.sleep(POLL_INTERVAL)
                continue

            response = coin_acceptor.read_buffer()
            event = events.process(response)

            if event is not None:
                if event.is_coin_inserted:
                    log.info(
                        "COIN INSERTED: counter=%s coin=%s path=%s",
                        event.event_counter,
                        event.coin_number,
                        event.sorter_path,
                    )
                else:
                    log.info(
                        "COIN ACCEPTOR EVENT: counter=%s error=%s",
                        event.event_counter,
                        event.sorter_path,
                    )

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        log.info("Stopping...")

    finally:
        transport.close()
        log.info("COM port closed.")

if __name__ == "__main__":
    main()
