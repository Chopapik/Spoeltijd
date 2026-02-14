"""HTML rewriting: asset URLs to Wayback and injection of stealth script + footer."""

import re
import datetime
from urllib.parse import urljoin


def inject_wayback_tags(html_bytes: bytes, base_url: str, year: str) -> bytes:
    """
    Rewrite src/href in HTML so assets load via Wayback (im_/js_/cs_ prefixes).
    Add year-check script (reload on change) and footer.
    """
    try:
        html_str = html_bytes.decode("utf-8", errors="ignore")

        pattern = r'(src|href)=([\"\'])(.*?)([\"\'])'

        def replacer(match):
            attr_name = match.group(1)
            quote = match.group(2)
            url = match.group(3)

            if (
                not url
                or url.startswith("#")
                or url.lower().startswith("javascript:")
                or "web.archive.org" in url
            ):
                return match.group(0)

            clean_ext = url.split("?")[0].split(".")[-1].lower()
            if clean_ext in ["jpg", "jpeg", "gif", "png", "bmp", "ico", "tif", "tiff"]:
                mod = "im_"
            elif clean_ext in ["js"]:
                mod = "js_"
            elif clean_ext in ["css"]:
                mod = "cs_"
            else:
                return match.group(0)

            absolute_url = urljoin(base_url, url)
            if not absolute_url.startswith("http"):
                return match.group(0)

            new_url = f"/web/{year}{mod}/{absolute_url}"
            return f"{attr_name}={quote}{new_url}{quote}"

        patched_html = re.sub(pattern, replacer, html_str, flags=re.IGNORECASE)

        # Remove legacy meta refresh; we use our own refresh logic.
        if re.search(
            r'<meta[^>]*http-equiv=["\']?refresh["\']?[^>]*>',
            patched_html,
            re.IGNORECASE,
        ):
            patched_html = re.sub(
                r'<meta[^>]*http-equiv=["\']?refresh["\']?[^>]*>',
                "",
                patched_html,
                flags=re.IGNORECASE,
            )

        stealth_script = f"""
            <script language="JavaScript">
            <!--
            var spoeltijdYear = {year};
            function spoeltijdPoll() {{
              var img = new Image();
              img.onload = function() {{
                var w = (typeof img.width !== "undefined") ? img.width : 0;
                var h = (typeof img.height !== "undefined") ? img.height : 0;
                if (w > 1 || h > 1) {{ location.reload(); }}
              }};
              img.src = "/spoeltijd/pixel?y=" + spoeltijdYear + "&t=" + (new Date().getTime());
            }}
            setInterval(spoeltijdPoll, 1500);
            spoeltijdPoll();
            // -->
            </script>
            """

        footer = (
            f'<div style="position:fixed;bottom:0;left:0;right:0;background:#fff;color:#000;'
            f'font-family:Times New Roman,Times,serif;font-size:12px;padding:2px;text-align:center;z-index:9999;">'
            f'* SPOELTIJD * | {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            f'</div>'
        )

        injection = footer + stealth_script

        if re.search(r"</body>", patched_html, re.IGNORECASE):
            patched_html = re.sub(
                r"(</body>)",
                injection + r"\1",
                patched_html,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            patched_html = patched_html + injection

        return patched_html.encode("utf-8")

    except Exception as e:
        print(f"[!] Regex rewrite error: {e}")
        return html_bytes
