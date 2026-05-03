"""Update search.json and feed.xml in the myerman-art repo."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .config import SEARCH_JSON, FEED_XML, SITE_BASE_URL


def update_search(slug: str, title: str, tags: list[str], description: str, date: str) -> bool:
    """Prepend a new entry to search.json. Returns True if added, False if slug already exists."""
    data = json.loads(SEARCH_JSON.read_text(encoding="utf-8"))

    if any(item["slug"] == slug for item in data):
        return False

    data.insert(0, {
        "slug": slug,
        "title": title,
        "tags": tags,
        "story": description,
        "date": date,
    })

    SEARCH_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def update_feed(slug: str, title: str, description: str) -> bool:
    """Prepend a new <item> to feed.xml. Returns True if added, False if already present."""
    xml = FEED_XML.read_text(encoding="utf-8")

    url = f"{SITE_BASE_URL}/prints/{slug}/"
    if url in xml:
        return False

    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y 12:00:00 +0000")
    thumb_url = f"{SITE_BASE_URL}/prints/{slug}/{slug}-thumb.jpg"

    item = (
        f'\n  <item>\n'
        f'    <title>{_escape(title)}</title>\n'
        f'    <link>{url}</link>\n'
        f'    <guid isPermaLink="true">{url}</guid>\n'
        f'    <pubDate>{pub_date}</pubDate>\n'
        f'    <description>{_escape(description)}</description>\n'
        f'    <enclosure url="{thumb_url}" type="image/jpeg" length="0"/>\n'
        f'  </item>'
    )

    # Insert after the <channel> opening block, before the first <item>
    xml = re.sub(r'(\n  <item>)', item + r'\1', xml, count=1)
    FEED_XML.write_text(xml, encoding="utf-8")
    return True


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
