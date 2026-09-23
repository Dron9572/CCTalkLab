# CCTalkLab

**CCtalk development, diagnostic and bus analysis tool**

CCTalkLab is an engineering tool for working with devices based on the **CCtalk serial protocol**.

The project aims to provide a modern, cross-platform alternative to legacy CCtalk host and diagnostic tools, with a focus on device development, testing, troubleshooting and bus analysis.

The initial implementation is being developed in **Python** with a graphical user interface. A **C++ implementation** is planned for the future.

---

## Project Status

> **Early development**

CCTalkLab is currently in the initial development stage.

The project structure and core architecture are being established first. CCtalk communication, device support and diagnostic functionality will be added progressively.

The API, user interface and internal architecture may change during development.

---

## Goals

The main goal of CCTalkLab is to provide a single engineering environment for three primary tasks:

### EMULATE

Operate as a CCtalk host/master and communicate directly with slave devices.

### MONITOR

Observe and analyze communication on a CCtalk bus.

### DIAGNOSE

Inspect connected devices and provide tools for troubleshooting and development.

```text
                 CCTalkLab
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
     EMULATE      MONITOR      DIAGNOSE
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
                 CCtalk Bus
                     │
              ┌──────┴──────┐
              │             │
           Host/Master    Slave
```

---

## Planned Features

### Host Emulator

CCTalkLab will be able to operate as a CCtalk host and communicate with slave devices.

Planned functionality:

* Send CCtalk commands
* Receive and decode responses
* Monitor communication in real time
* Display packet structure
* Calculate and verify checksums
* Execute predefined command sequences

### Bus Monitor / Sniffer

The bus monitoring mode will allow CCtalk communication to be observed and analyzed.

Planned functionality:

* Monitor CCtalk traffic
* Display transmitted and received packets
* Decode packet fields
* Display command headers and parameters
* Filter communication
* Search communication logs
* Record communication sessions
* Replay recorded sessions

### Device Inspector

The diagnostic interface will provide information about connected CCtalk devices.

For coin acceptors, planned information may include:

* Manufacturer
* Equipment category
* Model
* Serial number
* Firmware information
* Supported commands
* Coin configuration
* Coin channels
* Denominations
* Device status
* Error information

### Command Console

A key feature of CCTalkLab will be the ability to manually construct and send CCtalk commands to a slave device.

This will allow engineers to test individual commands without requiring a complete host application.

Possible use cases include:

* Device development
* Protocol investigation
* Troubleshooting
* Firmware testing
* Verifying device behaviour
* Testing undocumented commands
* Manual device configuration

---

## Roadmap

The following roadmap describes the planned development direction and does not necessarily represent the current implementation status.

* [ ] Project foundation
* [ ] Graphical user interface
* [ ] Serial communication layer
* [ ] CCtalk packet implementation
* [ ] CCtalk host emulator
* [ ] Packet decoder
* [ ] Real-time communication monitor
* [ ] Manual command console
* [ ] Device information reader
* [ ] Coin acceptor diagnostics
* [ ] Coin configuration reader
* [ ] Communication logging
* [ ] Session recording
* [ ] Session replay
* [ ] Packet filtering and search
* [ ] Custom command definitions
* [ ] Automated command sequences
* [ ] CCtalk bus sniffer
* [ ] Automated device tests
* [ ] Cross-platform packaging
* [ ] Native C++ implementation

---

## Architecture

The project is intended to separate the CCtalk protocol and communication layers from the graphical interface.

The initial architecture will follow a structure similar to:

```text
                    ┌─────────────────────┐
                    │     CCTalkLab UI    │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        ┌───────────┐    ┌───────────┐    ┌────────────┐
        │   Host    │    │  Monitor  │    │ Diagnostics│
        │  Emulator │    │  /Sniffer │    │  & Console │
        └─────┬─────┘    └─────┬─────┘    └──────┬─────┘
              │                │                 │
              └────────────────┼─────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │   CCtalk Protocol   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Transport / Serial │
                    └──────────┬──────────┘
                               │
                               ▼
                          CCtalk Bus
```

The protocol layer should remain independent of the GUI wherever practical.

This separation is intended to make the protocol implementation reusable and simplify the future C++ implementation.

---

## Project Structure

The initial project structure is intentionally small:

```text
CCTalkLab/
├── README.md
├── .gitignore
├── pyproject.toml
│
├── src/
│   └── cctalklab/
│       ├── __init__.py
│       └── main.py
│
└── tests/
    └── __init__.py
```

The structure will evolve as new functionality is implemented.

---

## Technology

### Current

* Python 3.11+
* Graphical user interface — in development
* Serial communication — planned

### Future

* Native C++ implementation
* Cross-platform distribution
* Automated testing and builds

---

## Supported Platforms

The project is intended to be cross-platform.

Initial development and testing will target:

* Windows
* Linux

Additional platforms may be supported in the future.

---

## Why CCTalkLab?

CCtalk devices are still used in vending, payment and other equipment, but many existing development and diagnostic tools are based on older software and operating-system environments.

CCTalkLab is intended to provide a modern and maintainable tool for engineers working with CCtalk devices.

The project focuses on combining:

* Host emulation
* Bus monitoring
* Protocol analysis
* Device diagnostics
* Manual command execution
* Communication logging

into a single application.

---

## Development

Clone the repository:

```bash
git clone https://github.com/Dron9572/CCTalkLab.git
cd CCTalkLab
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install the project in editable mode:

```bash
python -m pip install --upgrade pip
pip install -e .
```

Run CCTalkLab:

```bash
cctalklab
```

---

## License

License information will be added when the project license is finalized.

---

## Disclaimer

CCTalkLab is an independent project and is not affiliated with or endorsed by the manufacturers of CCtalk devices or existing CCtalk software.

CCtalk is used as the name of the communication protocol supported by the project.

---

**CCTalkLab**

*Emulate. Monitor. Diagnose.*
