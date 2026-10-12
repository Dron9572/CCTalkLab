# Changelog

## Version 0.1.0

First refactoring based on a working prototype

## Version 0.1.3

Coin acceptor identity and coin-channel information for UI/diagnostics

What's added:

* CoinAcceptorInfo - an object with information about the device
* CoinChannelInfo - information about a separate coin channel
* Manufacturer request - 246 (0xF6)
* Product code request - 244 (0xF4)
* Serial number request - 242 (0xF2)
* Request for communication version - 004 (0x04)
* Equipement request - 245 (0xF5)
* Creation date request - 196 (0xC4)
* Base year request - 170 (0xAA)
* Build code request - 192 (0xC0)
* Soft version request - 241 (0xF1)
* Request for coin channel IDs - 184 (0xB8), for channels 1–16
* Output collected information to the console after initialization
