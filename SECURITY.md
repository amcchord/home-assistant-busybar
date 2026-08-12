# Security policy

## Supported versions

Security fixes are provided for the latest release.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do not open a public issue containing API keys, LAN addresses, serial numbers, Wi-Fi names, MAC addresses, or exploit details.

Include the integration version, Home Assistant version, BUSY Bar firmware/API version, impact, and minimal reproduction steps. You should receive an acknowledgement within seven days.

## Local API guidance

Prefer the BUSY Bar HTTP API's **Key** mode on shared or untrusted networks. Home Assistant stores the key in its config entry and sends it only to the configured device address. This project has no telemetry or cloud relay.

