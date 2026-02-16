"""
LCD display (16x2) over I2C.
Hardcoded address and port. Functions to clear and write text.
"""
from RPLCD.i2c import CharLCD

# Fixed I2C address and port for this LCD
ADDR_LCD = 0x27
PORT_I2C = 0


class Lcd:
    """16x2 character LCD. Use clear() and write_text() to change content."""

    def __init__(self):
        self._device = CharLCD(
            i2c_expander='PCF8574',
            address=ADDR_LCD,
            port=PORT_I2C,
            cols=16,
            rows=2,
            dotsize=8,
        )

    def clear(self):
        """Clear the screen."""
        self._device.clear()

    def write_text(self, text):
        """Write text. Use \\r\\n for second line."""
        self._device.write_string(text)
