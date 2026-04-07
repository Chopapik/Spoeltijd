# Spoeltijd

<p align="center">
  <img src="logo.svg" alt="Spoeltijd logo" width="320" />
</p>

<p align="center">
  <strong>A Raspberry Pi bridge between retro browsers and the archived web.</strong>
</p>

Spoeltijd lets old browsers open archived websites through a Raspberry Pi.  
It fetches pages from the Internet Archive and serves them back as simple HTTP.

## What it does

- works as an HTTP bridge for retro browsers
- fetches archived pages from the Wayback Machine
- handles modern HTTPS on the Raspberry Pi side
- sends plain HTTP back to the retro machine
- supports an optional hardware UI with LCD, OLEDs, and a rotary encoder
- supports transparent redirect from port **80** to port **8080**

## Hardware UI

Optional Raspberry Pi hardware panel:

- **16x2 LCD** at `0x27`
- **OLED 1** at `0x3C`
- **OLED 2** at `0x3D`
- **Rotary encoder** on GPIO `18` and `21`

## Quick setup on DietPi / Raspberry Pi

Clone the repository, enter the project directory, and run:

```bash
bash setup_network.sh
```

Reboot the Raspberry Pi:

```bash
reboot
```

After reboot, start Spoeltijd:

```bash
python3 start.py
```

## Retro PC connection

Connect the retro PC to the Raspberry Pi Ethernet port.

The setup script configures:

- `eth0` as `192.168.50.1`
- DHCP for the retro PC
- transparent HTTP redirect from port `80` to port `8080`

So the retro computer can use Spoeltijd through the Raspberry Pi bridge.

## Browser setup

You can use Spoeltijd in two ways:

### 1. Normal HTTP proxy

Set the retro browser to use:

- **Proxy host:** Raspberry Pi IP
- **Proxy port:** `8080`

### 2. Transparent redirect

The setup script can redirect retro HTTP traffic from port `80` to `8080`.

## Notes

- use **HTTP only**
- do **not** use SSL/HTTPS proxy in the retro browser
- Spoeltijd runs on port `8080`
- best used on Raspberry Pi with the hardware panel

<p align="center">
  <img src="https://github.com/user-attachments/assets/028e8c24-0df7-4424-b38b-1f6823855f3c" alt="Spoeltijd hardware" width="700" />
</p>
