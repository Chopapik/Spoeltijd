import datetime
import time

from core import Bridge
from panel import Panel


class App:
    def __init__(self, year_min=1995, current_year=2002):
        self.year_min = year_min
        self.year_max = datetime.datetime.now().year

        # Keep initial year behavior unchanged from the previous entrypoint.
        self.current_year = current_year
        self.last_year_state = None

        self.panel = Panel(self.year_min, self.year_max, self.current_year)
        self.bridge = Bridge(self.current_year)

    def _process_tick(self):
        steps = int(self.panel.encoder.steps)
        new_year = self.year_min + steps

        new_year = max(self.year_min, min(self.year_max, new_year))

        if new_year != self.panel.encoder.steps + self.year_min:
            self.panel.encoder.steps = new_year - self.year_min

        if new_year != self.last_year_state:
            self._on_year_changed(new_year)

    def _on_year_changed(self, new_year):
        print(f"Time Warp: {new_year}")

        self.panel.update_lcd(f"{new_year}")
        self.panel.update_oled(f"Rok docelowy:\n{new_year}")

        self.bridge.current_year = new_year
        self.last_year_state = new_year

    def run(self):
        self.bridge.start_server()

        try:
            while True:
                self._process_tick()
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nZamykanie systemu...")
            self.panel.update_lcd("SYSTEM HALTED")
