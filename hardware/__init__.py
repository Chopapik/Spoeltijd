"""
Hardware package: LCD, OLED1, OLED2, encoder.

On Raspberry Pi, this exports the real hardware classes. On a development
machine without Pi-only dependencies, it falls back to small in-memory mocks so
proxy-only and test workflows can import the project.
"""

from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


try:
    from .lcd import Lcd, ADDR_LCD
    from .oled1 import Oled1, ADDR_OLED_STATUS
    from .oled2 import Oled2, ADDR_OLED_GRAPH
    from .encoder import Encoder, PIN_CLK, PIN_DT
except ModuleNotFoundError as exc:
    logger.debug("Hardware libraries unavailable; using mock hardware: %s", exc)

    ADDR_LCD = 0x27
    ADDR_OLED_STATUS = 0x3C
    ADDR_OLED_GRAPH = 0x3D
    PIN_CLK = 18
    PIN_DT = 21

    class Lcd:
        def __init__(self) -> None:
            self.text = ""

        def clear(self) -> None:
            self.text = ""

        def write_text(self, text) -> None:
            self.text = str(text)

    class _MockOled:
        width = 128
        height = 64

        def __init__(self) -> None:
            self.text = ""

        def clear(self) -> None:
            self.text = ""

        def fill(self, color="black") -> None:
            return None

        def draw_text(self, text, x=0, y=0, fill="white") -> None:
            self.text = str(text)

        def draw_rect(self, xy, outline=None, fill=None) -> None:
            return None

    class Oled1(_MockOled):
        pass

    class Oled2(_MockOled):
        pass

    class Encoder:
        def __init__(self, max_steps, initial_steps=0) -> None:
            self._max_steps = int(max_steps)
            self._steps = max(0, min(self._max_steps, int(initial_steps)))

        @property
        def steps(self) -> int:
            return self._steps

        @steps.setter
        def steps(self, value) -> None:
            self._steps = max(0, min(self._max_steps, int(value)))

        @property
        def max_steps(self) -> int:
            return self._max_steps


__all__ = [
    "Lcd", "ADDR_LCD",
    "Oled1", "ADDR_OLED_STATUS",
    "Oled2", "ADDR_OLED_GRAPH",
    "Encoder", "PIN_CLK", "PIN_DT",
]
