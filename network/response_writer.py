"""Small HTTP/1.0 response writer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


REASONS = {
    200: "OK",
    302: "Found",
    400: "Bad Request",
    404: "Not Found",
    502: "Bad Gateway",
}


class ResponseWriter:
    def __init__(self, request_socket) -> None:
        self.request_socket = request_socket

    def send(
        self,
        body: bytes = b"",
        status_code: int = 200,
        reason: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
    ) -> None:
        response_headers = dict(headers or {})
        if content_type:
            response_headers["Content-Type"] = content_type
        response_headers["Content-Length"] = str(len(body))
        response_headers["Connection"] = "close"

        status_reason = reason or REASONS.get(status_code, "OK")
        lines = [f"HTTP/1.0 {status_code} {status_reason}"]
        lines.extend(f"{name}: {value}" for name, value in response_headers.items())
        self.request_socket.sendall(
            "\r\n".join(lines).encode("utf-8") + b"\r\n\r\n" + body
        )

    def send_json(self, payload: Dict[str, Any]) -> None:
        self.send(
            json.dumps(payload).encode("utf-8"),
            content_type="application/json; charset=utf-8",
        )

    def send_redirect(self, location: str) -> None:
        self.send(status_code=302, headers={"Location": location})

    def send_file(self, path: str) -> None:
        file_path = Path(path)
        try:
            body = file_path.read_bytes()
        except OSError:
            self.send_error(404, "config.html not found")
            return

        self.send(body, content_type="text/html; charset=utf-8")

    def send_error(self, status_code: int, message: str) -> None:
        body = (
            "<html><body>"
            f"<h1>Spoeltijd error</h1><p>{message}</p>"
            "</body></html>"
        ).encode("utf-8")
        self.send(
            body,
            status_code=status_code,
            content_type="text/html; charset=utf-8",
        )
