"""
OLED display (second). Fixed I2C address.
Universal API: clear, draw_text, draw_rect, fill. Same interface as Oled1.
"""
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306

ADDR_OLED_GRAPH = 0x3D
PORT_I2C = 0


class Oled2:
    """Universal OLED. clear(), draw_text(), draw_rect(), fill(). Size via .width / .height."""

    def __init__(self):
        self._device = ssd1306(i2c(port=PORT_I2C, address=ADDR_OLED_GRAPH))

    @property
    def width(self):
        return self._device.width

    @property
    def height(self):
        return self._device.height

    def clear(self):
        """Clear display (fill black)."""
        with canvas(self._device) as draw:
            draw.rectangle(self._device.bounding_box, outline="black", fill="black")

    def fill(self, color="black"):
        """Fill entire display with color ('black' or 'white')."""
        with canvas(self._device) as draw:
            draw.rectangle(self._device.bounding_box, outline=color, fill=color)

    def draw_text(self, text, x=0, y=0, fill="white"):
        """Draw text at (x, y). fill: 'white' or 'black'."""
        with canvas(self._device) as draw:
            draw.text((x, y), text, fill=fill)

    def draw_rect(self, xy, outline=None, fill=None):
        """Draw rectangle. xy = (x1, y1, x2, y2). outline/fill: 'white' or 'black'."""
        with canvas(self._device) as draw:
            kwargs = {}
            if outline is not None:
                kwargs["outline"] = outline
            if fill is not None:
                kwargs["fill"] = fill
            draw.rectangle(xy, **kwargs)
