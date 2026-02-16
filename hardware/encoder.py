"""
Rotary encoder. Fixed GPIO pins.
Universal encoder that only manages step state.
"""
from gpiozero import RotaryEncoder

PIN_CLK = 18
PIN_DT = 21


class Encoder:
    """
    Universal rotary encoder.
    Only manages step state. Use steps property to get/set current position.
    """

    def __init__(self, max_steps, initial_steps=0):
        self._encoder = RotaryEncoder(
            PIN_CLK, PIN_DT,
            wrap=False,
            max_steps=max_steps,
        )
        self._encoder.steps = max(0, min(max_steps, int(initial_steps)))

    @property
    def steps(self):
        """Current step position."""
        return int(self._encoder.steps)

    @steps.setter
    def steps(self, value):
        """Set step position (clamped to valid range)."""
        max_steps = self._encoder.max_steps
        value = max(0, min(max_steps, int(value)))
        self._encoder.steps = value

    @property
    def max_steps(self):
        """Maximum number of steps."""
        return self._encoder.max_steps
