"""HTTP request parsing for the Spoeltijd proxy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
from urllib.parse import ParseResult, parse_qs, urlparse


class RequestParseError(ValueError):
    """Raised when a browser request cannot be parsed."""


@dataclass(frozen=True)
class HttpRequest:
    method: str
    target: str
    version: str
    host_header: str
    full_url: str
    parsed_url: ParseResult
    path: str
    query_params: Dict[str, List[str]]


def parse_http_request(request_data: bytes) -> HttpRequest:
    header_block = request_data.split(b"\r\n\r\n", 1)[0].decode(
        "utf-8", errors="ignore"
    )
    lines = header_block.split("\r\n")
    if not lines or not lines[0].strip():
        raise RequestParseError("empty request")

    try:
        method, target, version = lines[0].split(" ", 2)
    except ValueError as exc:
        raise RequestParseError(f"bad request line: {lines[0]!r}") from exc

    host_header = ""
    for header in lines[1:]:
        if header.lower().startswith("host:"):
            host_header = header.split(":", 1)[1].strip()
            break

    full_url = target
    if not full_url.startswith("http"):
        full_url = f"http://{host_header}{full_url}"

    parsed = urlparse(full_url)
    return HttpRequest(
        method=method,
        target=target,
        version=version,
        host_header=host_header,
        full_url=full_url,
        parsed_url=parsed,
        path=parsed.path,
        query_params=parse_qs(parsed.query),
    )
