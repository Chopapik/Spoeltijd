import os
from urllib.parse import urlparse

def get_archive_url(raw_url_bytes, target_year="2002"):
    """
    Spoeltijd Proxy decision engine.
    Splits the URL, analyzes file type and selects the ideal Wayback Machine modifier.
    Returns: (ready_url_to_download, parsedUrl_object)
    """
    # 1. Decoding raw bytes from the socket
    if isinstance(raw_url_bytes, bytes):
        url_str = raw_url_bytes.decode("utf-8", errors="ignore")
    else:
        url_str = raw_url_bytes
        
    parsedUrl = urlparse(url_str)
    path = parsedUrl.path.lower()
    netloc = parsedUrl.netloc
    query = parsedUrl.query

    print("\n" + "=" * 55)
    print(f"[PARSER IN] Client requests: {netloc}{path}")

    # 2. Bypass for URLs that Wayback has already processed in HTML
    if path.startswith("/web/"):
        fetch_url = "https://web.archive.org" + parsedUrl.path
        if query: 
            fetch_url += "?" + query
        print("[PARSER OUT] Archive link detected. Passing through cleanly (Passthrough).")
        print(f"-> Target: {fetch_url}")
        print("=" * 55)
        return fetch_url, parsedUrl

    # 3. Extension analysis (Hard interrupts for file types)
    _, ext = os.path.splitext(path)

    if ext in ['.gif', '.jpg', '.jpeg', '.png', '.bmp', '.ico']:
        modifier = "im_"
        file_type = "Image (im_)"
        
    elif ext in ['.css']:
        modifier = "cs_"
        file_type = "CSS Sheet (cs_)"
        
    elif ext in ['.js']:
        modifier = "js_"
        file_type = "JS Script (js_)"
        
    elif ext in ['.swf', '.class', '.cab', '.dcr']:
        # Loading heavy artillery for Flash and Java
        modifier = "oe_"
        file_type = "Object/Flash (oe_)"
        
    else:
        modifier = "id_"
        file_type = "HTML/Raw Data (id_)"

    # 4. Composing the final request
    fetch_url = f"https://web.archive.org/web/{target_year}{modifier}/{netloc}{parsedUrl.path}"
    if query: 
        fetch_url += "?" + query

    print(f"[PARSER OUT] Type: {file_type} | Modifier applied: {modifier}")
    print(f"-> Target: {fetch_url}")
    print("=" * 55)

    return fetch_url, parsedUrl