import unittest
from unittest.mock import Mock

import requests

from archive.asset_client import AssetClient
from archive.asset_url import clean_http_asset_url, is_asset_url
from cache import CachedResponse


def make_response(status_code=200, content=b"asset", content_type="image/gif"):
    response = requests.Response()
    response.status_code = status_code
    response._content = content
    response.headers["Content-Type"] = content_type
    response.reason = "OK" if status_code == 200 else "Not Found"
    response.url = "http://example.com/logo.gif"
    return response


class AssetUrlTests(unittest.TestCase):
    def test_detects_asset_urls_by_extension(self):
        for url in [
            "http://example.com/logo.gif",
            "http://example.com/photo.jpg",
            "http://example.com/photo.jpeg",
            "http://example.com/image.png",
            "http://example.com/image.bmp",
            "http://example.com/favicon.ico",
            "http://example.com/image.webp",
            "http://example.com/site.css",
            "http://example.com/app.js",
            "http://example.com/movie.swf",
            "http://example.com/Applet.class",
            "http://example.com/control.cab",
            "http://example.com/media.dcr",
            "http://example.com/sound.wav",
            "http://example.com/music.mid",
            "http://example.com/audio.mp3",
            "http://example.com/logo.gif?v=1",
        ]:
            with self.subTest(url=url):
                self.assertTrue(is_asset_url(url))

        self.assertFalse(is_asset_url("http://example.com/page.html"))

    def test_https_asset_is_converted_to_http(self):
        self.assertEqual(
            clean_http_asset_url("https://example.com/logo.gif?v=1"),
            "http://example.com/logo.gif?v=1",
        )


class AssetClientTests(unittest.TestCase):
    def test_direct_200_means_wayback_is_not_called(self):
        session = Mock()
        session.get.return_value = make_response(status_code=200, content=b"asset")
        wayback_client = Mock()

        response = AssetClient(session, wayback_client).fetch(
            "http://example.com/logo.gif",
            "2002",
        )

        self.assertEqual(response.content, b"asset")
        wayback_client.fetch.assert_not_called()

    def test_https_asset_uses_http_for_direct_request(self):
        session = Mock()
        session.get.return_value = make_response(status_code=200, content=b"asset")
        wayback_client = Mock()

        AssetClient(session, wayback_client).fetch(
            "https://example.com/logo.gif",
            "2002",
        )

        session.get.assert_called_once_with(
            "http://example.com/logo.gif",
            stream=False,
            timeout=5,
            allow_redirects=True,
        )

    def test_direct_404_falls_back_to_wayback(self):
        session = Mock()
        session.get.return_value = make_response(status_code=404, content=b"missing")
        wayback_client = Mock()
        wayback_client.fetch.return_value = CachedResponse(
            status_code=200,
            headers={"Content-Type": "image/gif"},
            content=b"archived",
        )

        response = AssetClient(session, wayback_client).fetch(
            "http://example.com/logo.gif",
            "2002",
        )

        self.assertEqual(response.content, b"archived")
        wayback_client.fetch.assert_called_once_with(
            "http://example.com/logo.gif",
            "2002",
        )

    def test_direct_timeout_falls_back_to_wayback(self):
        session = Mock()
        session.get.side_effect = requests.Timeout("timed out")
        wayback_client = Mock()
        wayback_client.fetch.return_value = CachedResponse(
            status_code=200,
            headers={"Content-Type": "image/gif"},
            content=b"archived",
        )

        response = AssetClient(session, wayback_client).fetch(
            "http://example.com/logo.gif",
            "2002",
        )

        self.assertEqual(response.content, b"archived")
        wayback_client.fetch.assert_called_once_with(
            "http://example.com/logo.gif",
            "2002",
        )


if __name__ == "__main__":
    unittest.main()
