"""Spoeltijd command-line entrypoint."""

from __future__ import annotations

import argparse
import logging
from typing import Optional, Sequence

from core import Bridge


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start Spoeltijd.")
    parser.add_argument("--year", type=int, default=2002, help="Initial target year.")
    parser.add_argument(
        "--no-panel",
        action="store_true",
        help="Run the proxy without LCD/OLED/encoder hardware.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args(argv)

    if args.no_panel:
        logging.info("Starting proxy only (no app/panel)...")
        Bridge(args.year).serve_forever()
        return

    from app import App

    App(current_year=args.year).run()


if __name__ == "__main__":
    main()
