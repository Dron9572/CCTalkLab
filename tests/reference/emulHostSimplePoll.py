import serial
import time


PORT = "COM3"


def checksum(data):
    return (-sum(data)) & 0xFF


def make_packet(destination, source, command, data=b""):
    packet = bytearray()

    packet.append(destination)
    packet.append(len(data))
    packet.append(source)
    packet.append(command)
    packet.extend(data)

    packet.append(checksum(packet))

    return packet


with serial.Serial(
    port=PORT,
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=0.05,
    xonxoff=False,
    rtscts=False,
    dsrdtr=False,
) as ser:

    ser.dtr = True
    ser.rts = True

    print(f"Connected to {PORT}")

    while True:

        # Simple Poll
        packet = make_packet(
            destination=2,
            source=1,
            command=0xFE,
        )

        print("TX:", packet.hex(" "))

        ser.write(packet)

        response = ser.read(256)

        if response:
            print("RX:", response.hex(" "))
        else:
            print("RX: <timeout>")

        time.sleep(0.1)