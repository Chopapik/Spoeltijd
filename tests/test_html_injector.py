import unittest

from archive.html_injector import inject_wayback_tags


class HtmlInjectorTests(unittest.TestCase):
    def test_rewrites_asset_urls_to_clean_http(self):
        body = (
            b'<html><body><img src="https://example.com/logo.gif">'
            b'<link href="/site.css"></body></html>'
        )

        injected = inject_wayback_tags(
            body,
            base_url="http://example.com/page.html",
            year="2002",
        ).decode("utf-8")

        self.assertIn('src="http://example.com/logo.gif"', injected)
        self.assertIn('href="http://example.com/site.css"', injected)
        self.assertNotIn("/web/2002", injected)


if __name__ == "__main__":
    unittest.main()
