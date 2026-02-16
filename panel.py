"""
Panel: LCD, OLED, encoder combined for display and input.
Uses hardware classes for devices; maps encoder steps to year range.
"""

from hardware import Lcd, Oled1, Oled2, Encoder


class Panel:
    """Control panel: LCD, OLED1, OLED2, encoder. Manages displayed year from encoder."""

    def __init__(self, year_min, year_max, target_year):
        self.year_min = year_min
        self.year_max = year_max
        total_steps = year_max - year_min
        initial_steps = target_year - year_min

        self.lcd = Lcd()
        self.oled_status = Oled1()
        self.oled_graph = Oled2()
        self.encoder = Encoder(max_steps=total_steps, initial_steps=initial_steps)

    def update_lcd(self, text):
        """Update LCD display with text."""
        self.lcd.clear()
        self.lcd.write_text(text)

    def update_oled(self, text):
        """Update OLED status display with text."""
        self.oled_status.draw_text(text, x=5, y=5)

    def get_current_year(self):
        """Get current year from encoder steps."""
        return self.year_min + self.encoder.steps
