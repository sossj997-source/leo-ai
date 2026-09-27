def get_top_five_headlines(url: str) -> list | str:
    """Fetch RSS feed and return the top 5 headlines."""
    try:
        import requests, xml.etree.ElementTree as ET
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        # RSS can be <rss><channel><item>... or Atom <feed><entry>
        items = root.findall('.//item') or root.findall('.//entry')
        headlines = []
        for item in items[:5]:
            title = item.find('title')
            if title is not None and title.text:
                headlines.append(title.text.strip())
        return headlines
    except Exception as e:
        return f"Error: {e}"