"""
Hardware logic: LCD, OLED, rotary encoder, main UI loop.
Uses nat module for TARGET_YEAR and proxy thread.
"""

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from RPLCD.i2c import CharLCD
from gpiozero import RotaryEncoder
import threading 


class Hardware:
    PIN_CLK = 18
    PIN_DT = 21
    PORT_I2C = 0  # Change to 1 in newer Raspberry Pi revisions  

    ADDR_LCD = 0x27
    ADDR_OLED_STATUS = 0x3C
    ADDR_OLED_GRAPH = 0x3D

    def __init__(self, year_min, year_max, target_year):
        total_steps = year_max - year_min
        self.lcd = CharLCD(
            i2c_expander='PCF8574', 
            address=Hardware.ADDR_LCD, 
            port=Hardware.PORT_I2C,
            cols=16, rows=2, dotsize=8
        )
        self.oled_status = ssd1306(i2c(
            port=Hardware.PORT_I2C, address=self.ADDR_OLED_STATUS
        ))
        self.oled_graph = ssd1306(i2c(
            port=Hardware.PORT_I2C, address=Hardware.ADDR_OLED_GRAPH
        ))
        self.encoder = RotaryEncoder(
            Hardware.PIN_CLK, Hardware.PIN_DT,
            wrap=False, max_steps=total_steps
        )
        self.encoder.steps = target_year - year_min

    def update_lcd(self, text):
        self.lcd.clear()
        self.lcd.write_string(text)

    def update_oled(self, text):
        with canvas(self.oled_status) as draw:
            draw.rectangle(self.oled_status.bounding_box, outline="white", fill="black")
            draw.text((5, 5), text, fill="white")
    
    def get_current_year(self):
        return self.encoder.steps + self.year_min

