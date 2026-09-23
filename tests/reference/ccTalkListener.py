import serial


PORT = "COM3"

with serial.Serial(
    port=PORT,
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1,
) as ser:

    print("Listening...")

    while True:
        data = ser.read(256)

        if data:
            print("RX:", data.hex(" "))