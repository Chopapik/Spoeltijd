"""Compatibility wrapper for proxy-only startup."""

from start import main


if __name__ == "__main__":
    main(["--no-panel"])
