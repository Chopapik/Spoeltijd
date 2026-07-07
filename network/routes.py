"""Route dispatching for Spoeltijd proxy requests."""

from __future__ import annotations

import logging
import os
from typing import Optional

from archive.html_injector import inject_wayback_tags
from archive.wayback_client import WaybackFetchError
from core.constants import GIF_1X1, GIF_2X2

from .request_parser import HttpRequest
from .response_writer import ResponseWriter


logger = logging.getLogger(__name__)


class Router:
    def __init__(self, bridge) -> None:
        self.bridge = bridge

    def dispatch(self, request: HttpRequest, writer: ResponseWriter) -> None:
        if request.method == "CONNECT":
            return

        path = request.path.rstrip("/")
        parsed_host = request.parsed_url.netloc.split(":", 1)[0].lower()
        header_host = request.host_header.split(":", 1)[0].lower()
        is_config_host = (
            parsed_host == "spoeltijd.config" or header_host == "spoeltijd.config"
        )

        if is_config_host and path == "":
            self._handle_config_page(writer)
            return
        if is_config_host and path == "/year":
            self._handle_year(writer)
            return
        if is_config_host and path == "/save":
            self._handle_save_config(request, writer)
            return

        if path == "/spoeltijd/pixel":
            self._handle_pixel(request, writer)
            return
        if path == "/spoeltijd/year":
            self._handle_year(writer)
            return
        if path == "/spoeltijd/config":
            self._handle_config_page(writer)
            return
        if path == "/spoeltijd/config/save":
            self._handle_save_config(request, writer)
            return

        self._handle_wayback_proxy(request, writer)

    def _handle_pixel(self, request: HttpRequest, writer: ResponseWriter) -> None:
        client_timestamp = self._client_timestamp(request)
        current_timestamp = self.bridge.current_timestamp
        if current_timestamp == client_timestamp:
            img_data = GIF_1X1
        else:
            logger.info("Reload signal triggered for timestamp %s", current_timestamp)
            img_data = GIF_2X2

        writer.send(
            img_data,
            content_type="image/gif",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    def _client_timestamp(self, request: HttpRequest) -> str:
        y_values = request.query_params.get("y", [])
        if y_values:
            try:
                return str(int(y_values[0]))
            except (ValueError, IndexError):
                pass

        t_values = request.query_params.get("t", [])
        if t_values:
            return str(t_values[0]).strip()
        return ""

    def _handle_year(self, writer: ResponseWriter) -> None:
        year, month, day = self.bridge.state.snapshot()
        writer.send_json(
            {
                "year": year,
                "month": month,
                "day": day,
                "timestamp": self.bridge.current_timestamp,
            }
        )

    def _handle_config_page(self, writer: ResponseWriter) -> None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "ui",
            "config.html",
        )
        writer.send_file(config_path)

    def _handle_save_config(
        self, request: HttpRequest, writer: ResponseWriter
    ) -> None:
        current_year, _, _ = self.bridge.state.snapshot()

        year = self._parse_year(request, current_year)
        month = self._parse_optional_int(request, "month", 1, 12)
        day = self._parse_optional_int(request, "day", 1, 31)
        if month is None:
            day = None

        self.bridge.state.update(year=year, month=month, day=day)
        writer.send_redirect("http://spoeltijd.config/")

    def _parse_year(self, request: HttpRequest, fallback: int) -> int:
        year_values = request.query_params.get("year", [])
        if not year_values:
            return fallback
        try:
            return int(year_values[0])
        except (ValueError, IndexError):
            return fallback

    def _parse_optional_int(
        self,
        request: HttpRequest,
        name: str,
        minimum: int,
        maximum: int,
    ) -> Optional[int]:
        values = request.query_params.get(name, [])
        raw_value = values[0].strip() if values else ""
        if raw_value == "":
            return None

        try:
            candidate = int(raw_value)
        except ValueError:
            return None
        return candidate if minimum <= candidate <= maximum else None

    def _handle_wayback_proxy(
        self, request: HttpRequest, writer: ResponseWriter
    ) -> None:
        try:
            response = self.bridge.wayback_client.fetch(
                request.full_url,
                self.bridge.current_timestamp,
            )
        except WaybackFetchError:
            writer.send_error(502, "Could not fetch the archived page.")
            return

        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" in content_type:
            body = inject_wayback_tags(
                response.content,
                base_url=request.full_url,
                year=self.bridge.current_timestamp,
            )
            writer.send(
                body,
                status_code=response.status_code,
                reason=response.reason,
                content_type=response.headers.get("Content-Type", "text/html"),
            )
            return

        headers = {}
        if response.headers.get("Content-Length"):
            headers["Content-Length"] = response.headers["Content-Length"]
        writer.send(
            response.content,
            status_code=response.status_code,
            reason=response.reason,
            headers=headers,
            content_type=response.headers.get(
                "Content-Type", "application/octet-stream"
            ),
        )
