import unittest
from unittest.mock import Mock

from cache import CachedResponse
from network.request_parser import parse_http_request
from network.routes import Router


class FakeWriter:
    def __init__(self):
        self.sent = []
        self.errors = []

    def send(self, *args, **kwargs):
        self.sent.append((args, kwargs))

    def send_error(self, status_code, message):
        self.errors.append((status_code, message))


class RouterTests(unittest.TestCase):
    def test_html_document_uses_wayback_first(self):
        bridge = Mock()
        bridge.current_timestamp = "2002"
        bridge.wayback_client.fetch.return_value = CachedResponse(
            status_code=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            content=b"<html><body><h1>Hello</h1></body></html>",
        )
        request = parse_http_request(
            b"GET http://example.com/page.html HTTP/1.0\r\n"
            b"Host: example.com\r\n\r\n"
        )
        writer = FakeWriter()

        Router(bridge).dispatch(request, writer)

        bridge.wayback_client.fetch.assert_called_once_with(
            "http://example.com/page.html",
            "2002",
        )
        bridge.asset_client.fetch.assert_not_called()
        self.assertEqual(writer.errors, [])
        self.assertEqual(len(writer.sent), 1)

    def test_asset_url_uses_asset_client(self):
        bridge = Mock()
        bridge.current_timestamp = "2002"
        bridge.asset_client.fetch.return_value = CachedResponse(
            status_code=200,
            headers={"Content-Type": "image/gif"},
            content=b"asset",
        )
        request = parse_http_request(
            b"GET http://example.com/logo.gif HTTP/1.0\r\n"
            b"Host: example.com\r\n\r\n"
        )
        writer = FakeWriter()

        Router(bridge).dispatch(request, writer)

        bridge.asset_client.fetch.assert_called_once_with(
            "http://example.com/logo.gif",
            "2002",
        )
        bridge.wayback_client.fetch.assert_not_called()
        self.assertEqual(writer.errors, [])
        self.assertEqual(len(writer.sent), 1)


if __name__ == "__main__":
    unittest.main()
