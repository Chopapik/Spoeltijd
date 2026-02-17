from core import Bridge
from panel import Panel
import datetime
import time

def main():

    year_min = 1995
    year_max = datetime.datetime.now().year
    current_year = 2002

    panel = Panel(1995, year_max, current_year)
    bridge = Bridge(current_year)

    bridge.start_server()

    last_year_state = None

    try:
      while True:
        steps = int(panel.encoder.steps)
        new_year = year_min + steps

        new_year = max(year_min, min(year_max, new_year))

        if new_year != panel.encoder.steps + year_min:
            panel.encoder.steps = new_year - year_min

        if new_year != last_year_state:
            print(f"Time Warp: {new_year}")

            panel.update_lcd(f"{new_year}")
            panel.update_oled(f"Rok docelowy:\n{new_year}")

            bridge.current_year = new_year

            last_year_state = new_year

        time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nZamykanie systemu...")
        panel.update_lcd("SYSTEM HALTED")

if __name__ == "__main__":
    main()