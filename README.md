# Spoeltijd

<p align="center">
  <img src="logo.svg" alt="Spoeltijd" width="320" />
</p>

**Spoeltijd** is an HTTP **proxy bridge** that connects retro browsers to the Internet Archive (Wayback Machine). It acts as a gateway: on one side it handles modern HTTPS and Archive.org URLs, and on the other it serves content as plain **HTTP** in a format that old browsers understand (e.g. IE5, Netscape, Opera from the late 90s).

---

### How it works

- The retro browser is configured to use **Spoeltijd** as its HTTP proxy and opens a URL such as `http://google.com/`.
- The bridge intercepts the request, fetches the matching snapshot from the **Wayback Machine** for the chosen date (year, month, day), and returns it to the browser as plain HTTP.
- **HTTPS** and redirects are handled on the bridge side; the browser only sees simple HTTP and the archived page.

This way you can browse archived websites on vintage hardware or in an emulator exactly as they looked on a given day, without any SSL or modern protocol support on the client.

---

### Requirements

- **Python 3**
- **Raspberry Pi** (e.g. DietPi) with I²C enabled, for the optional hardware UI:
  - 16×2 LCD (e.g. PCF8574 at `0x27`)
  - Two SSD1306 OLEDs at `0x3C` and `0x3D`
  - Rotary encoder on GPIO 18 (CLK) and 21 (DT)

Without the hardware, you can run the proxy alone and change the snapshot year in code or via a future API.

---

### Install and run

```bash
pip install -r requirements.txt
python start.py
```

The proxy listens on **port 8080** (configurable in `core/constants.py`).

---

### Configure the retro browser

Set the HTTP proxy to the machine running Spoeltijd:

- **Proxy host:** IP of the Raspberry (e.g. `192.168.1.10`)
- **Proxy port:** `8080`
- Use **HTTP** proxy only (no SSL proxy).

Then open any URL, e.g. `http://google.com/` — you will get the archived snapshot for the year selected on the encoder (or the default in code).

---

### Hardware UI

<p align="center">
  <img src="https://github.com/user-attachments/assets/028e8c24-0df7-4424-b38b-1f6823855f3c" alt="hardware" width="600" />
</p>

*Spoeltijd* — a bridge between the old web and the archived one.
