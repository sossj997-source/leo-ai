def get_top5_rss_headlines(url: str) -> list:
    """Returns top 5 news headlines from the given RSS feed URL."""
    import urllib.request, xml.etree.ElementTree as ET
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        # Find all <item> elements (RSS) or <entry> (Atom)
        items = root.findall('.//item')
        if not items:
            items = root.findall('.//entry')
        headlines = []
        for item in items[:5]:
            title = item.find('title')
            if title is not None and title.text:
                headlines.append(title.text.strip())
        return headlines
    except Exception as e:
        return [f"Error: {e}"]