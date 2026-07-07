import unittest

from archive.wayback_url import build_wayback_url, detect_wayback_modifier


class WaybackUrlTests(unittest.TestCase):
    def test_detects_modifier_by_extension(self):
        self.assertEqual(detect_wayback_modifier("http://example.com/logo.gif"), "im_")
        self.assertEqual(detect_wayback_modifier("http://example.com/site.css"), "cs_")
        self.assertEqual(detect_wayback_modifier("http://example.com/app.js"), "js_")
        self.assertEqual(detect_wayback_modifier("http://example.com/movie.swf"), "oe_")
        self.assertEqual(detect_wayback_modifier("http://example.com/"), "id_")

    def test_detects_modifier_from_existing_archive_path(self):
        self.assertEqual(
            detect_wayback_modifier("/web/200201im_/http://example.com/logo.gif"),
            "im_",
        )

    def test_builds_regular_wayback_url(self):
        self.assertEqual(
            build_wayback_url("http://example.com/page.html?x=1", "2002"),
            "https://web.archive.org/web/2002id_/example.com/page.html?x=1",
        )

    def test_preserves_archive_passthrough_path(self):
        self.assertEqual(
            build_wayback_url(
                "http://example.com/web/2002im_/http://example.com/logo.gif",
                "2003",
            ),
            "https://web.archive.org/web/2002im_/http://example.com/logo.gif",
        )


if __name__ == "__main__":
    unittest.main()
